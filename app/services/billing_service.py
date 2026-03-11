"""Billing service – KOT generation, invoice creation."""

import uuid
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import KOT, KOTItem, Invoice
from app.models.orders import Order, OrderItem
from app.models.products import Product


async def _next_kot_number_for_order(db: AsyncSession, order_id: uuid.UUID) -> int:
    """Sequential KOT number per order: 1, 2, 3, …"""
    result = await db.execute(
        select(func.coalesce(func.max(KOT.kot_number), 0)).where(KOT.order_id == order_id)
    )
    return (result.scalar() or 0) + 1


async def create_kot(
    db: AsyncSession,
    order_id: uuid.UUID,
    store_id: uuid.UUID,
    item_ids: list[uuid.UUID] | None = None,
    kitchen_section: str | None = None,
) -> KOT:
    """
    Create a Kitchen Order Ticket for new/unsent order items.

    If item_ids is provided, only those items are included.
    Otherwise, all active items not yet assigned to a KOT are included.
    """
    kot_id = uuid.uuid4()
    kot_number = await _next_kot_number_for_order(db, order_id)

    # Fetch the order
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")
    if order.status in ("completed", "paid", "cancelled"):
        raise ValueError(f"Cannot create KOT for order in '{order.status}' status")

    # Build query for eligible items
    item_query = (
        select(OrderItem)
        .where(
            OrderItem.order_id == order_id,
            OrderItem.status == "active",
            OrderItem.kot_id.is_(None),
        )
    )
    if item_ids:
        item_query = item_query.where(OrderItem.id.in_(item_ids))

    result = await db.execute(item_query)
    order_items = result.scalars().all()

    if not order_items:
        raise ValueError("No unsent items available for KOT")

    # Resolve product names in one query
    product_ids = [oi.product_id for oi in order_items if oi.product_id]
    product_name_map: dict = {}
    if product_ids:
        prod_result = await db.execute(
            select(Product.id, Product.name).where(Product.id.in_(product_ids))
        )
        product_name_map = {row.id: row.name for row in prod_result}

    kot_items = []
    for oi in order_items:
        # Prefer stored product_name, then product lookup, then fallback
        name = (
            oi.product_name
            or product_name_map.get(oi.product_id, "Unknown Product")
        )
        kot_items.append(
            KOTItem(
                id=uuid.uuid4(),
                kot_id=kot_id,
                order_item_id=oi.id,
                product_name=name,
                quantity=oi.quantity,
                notes=oi.notes,
            )
        )
        # Link order item to this KOT and update kitchen status
        oi.kot_id = kot_id
        oi.kitchen_status = "sent"

    kot = KOT(
        id=kot_id,
        order_id=order_id,
        store_id=store_id,
        kot_number=kot_number,
        kitchen_section=kitchen_section,
        status="pending",
    )
    db.add(kot)
    db.add_all(kot_items)

    # If this is the first KOT for the order, transition to sent_to_kitchen
    if order.status == "open":
        order.status = "sent_to_kitchen"

    await db.flush()
    return kot


async def update_kot_status(
    db: AsyncSession, kot_id: uuid.UUID, new_status: str
) -> KOT:
    """
    Advance a KOT through its lifecycle: pending → preparing → ready.
    Also updates the linked order items' kitchen_status.
    """
    allowed_transitions = {
        "pending": {"preparing"},
        "preparing": {"ready"},
        "ready": set(),
    }
    result = await db.execute(
        select(KOT).options(selectinload(KOT.items)).where(KOT.id == kot_id)
    )
    kot = result.scalar_one_or_none()
    if not kot:
        raise ValueError("KOT not found")

    if new_status not in allowed_transitions.get(kot.status, set()):
        raise ValueError(f"Cannot transition KOT from '{kot.status}' to '{new_status}'")

    kot.status = new_status

    # Update kitchen_status on linked order items
    item_ids = [ki.order_item_id for ki in kot.items]
    if item_ids:
        items_result = await db.execute(
            select(OrderItem).where(OrderItem.id.in_(item_ids))
        )
        for oi in items_result.scalars().all():
            oi.kitchen_status = new_status

    await db.flush()
    return kot


async def get_kot(db: AsyncSession, kot_id: uuid.UUID) -> KOT | None:
    result = await db.execute(
        select(KOT).options(selectinload(KOT.items)).where(KOT.id == kot_id)
    )
    return result.scalar_one_or_none()


# ── Invoice ───────────────────────────────────────────────────────────────

async def _next_invoice_number(db: AsyncSession, store_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.store_id == store_id)
    )
    count = result.scalar() or 0
    return f"INV-{count + 1:06d}"


async def generate_invoice(db: AsyncSession, order_id: uuid.UUID) -> Invoice:
    """Generate an invoice from a completed order."""
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")

    # Build tax breakdown from items
    tax_breakdown: dict[str, float] = {}
    for item in order.items:
        key = f"tax_{item.tax_amount}"
        tax_breakdown[key] = tax_breakdown.get(key, 0) + float(item.tax_amount)

    invoice = Invoice(
        id=uuid.uuid4(),
        order_id=order.id,
        store_id=order.store_id,
        invoice_number=await _next_invoice_number(db, order.store_id),
        gross_amount=order.gross_amount,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        service_charge=order.service_charge,
        net_amount=order.net_amount,
        tax_breakdown=tax_breakdown,
    )
    db.add(invoice)
    await db.flush()
    return invoice
