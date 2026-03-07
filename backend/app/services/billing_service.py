"""Billing service – KOT generation, invoice creation."""

import uuid
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import KOT, KOTItem, Invoice
from app.models.orders import Order, OrderItem


async def _next_kot_number(db: AsyncSession, store_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count(KOT.id)).where(KOT.store_id == store_id)
    )
    count = result.scalar() or 0
    return f"KOT-{count + 1:04d}"


async def create_kot(
    db: AsyncSession,
    order_id: uuid.UUID,
    store_id: uuid.UUID,
    item_ids: list[uuid.UUID],
    kitchen_section: str | None = None,
) -> KOT:
    """Create a Kitchen Order Ticket for selected order items."""
    kot_id = uuid.uuid4()
    kot_number = await _next_kot_number(db, store_id)

    # Fetch order items
    result = await db.execute(
        select(OrderItem).where(OrderItem.id.in_(item_ids), OrderItem.order_id == order_id)
    )
    order_items = result.scalars().all()

    kot_items = []
    for oi in order_items:
        kot_items.append(
            KOTItem(
                id=uuid.uuid4(),
                kot_id=kot_id,
                order_item_id=oi.id,
                product_name=str(oi.product_id),  # enriched by caller / product lookup
                quantity=oi.quantity,
                notes=oi.notes,
            )
        )
        # Link order item to this KOT
        oi.kot_id = kot_id

    kot = KOT(
        id=kot_id,
        order_id=order_id,
        store_id=store_id,
        kot_number=kot_number,
        kitchen_section=kitchen_section,
        status="printed",
    )
    db.add(kot)
    db.add_all(kot_items)
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
