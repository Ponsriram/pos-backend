"""Purchasing service – vendors, purchase orders, receipts."""

import uuid
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchasing import (
    Vendor,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
)
from app.models.inventory import StockLevel
from app.schemas.purchasing_schema import (
    VendorCreate,
    VendorUpdate,
    PurchaseOrderCreate,
    PurchaseReceiptCreate,
)


# ── Vendors ───────────────────────────────────────────────────────────────

async def create_vendor(db: AsyncSession, payload: VendorCreate) -> Vendor:
    vendor = Vendor(id=uuid.uuid4(), **payload.model_dump())
    db.add(vendor)
    await db.flush()
    return vendor


async def update_vendor(db: AsyncSession, vendor: Vendor, payload: VendorUpdate) -> Vendor:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    await db.flush()
    return vendor


# ── Purchase Orders ───────────────────────────────────────────────────────

async def _next_po_number(db: AsyncSession, store_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(PurchaseOrder.store_id == store_id)
    )
    count = result.scalar() or 0
    return f"PO-{count + 1:04d}"


async def create_purchase_order(
    db: AsyncSession, payload: PurchaseOrderCreate, created_by: uuid.UUID | None = None
) -> PurchaseOrder:
    po_id = uuid.uuid4()
    total = Decimal("0")
    lines = []
    for line in payload.lines:
        line_total = Decimal(str(line.unit_price)) * Decimal(str(line.quantity))
        total += line_total
        lines.append(
            PurchaseOrderLine(
                id=uuid.uuid4(),
                purchase_order_id=po_id,
                item_id=line.item_id,
                quantity=line.quantity,
                unit_id=line.unit_id,
                unit_price=float(line.unit_price),
                total_price=float(line_total),
            )
        )

    po = PurchaseOrder(
        id=po_id,
        store_id=payload.store_id,
        vendor_id=payload.vendor_id,
        po_number=await _next_po_number(db, payload.store_id),
        status="draft",
        total_amount=float(total),
        notes=payload.notes,
        expected_delivery=payload.expected_delivery,
        created_by=created_by,
    )
    db.add(po)
    db.add_all(lines)
    await db.flush()
    return po


async def get_purchase_order(db: AsyncSession, po_id: uuid.UUID) -> PurchaseOrder | None:
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po_id)
    )
    return result.scalar_one_or_none()


# ── Purchase Receipts ─────────────────────────────────────────────────────

async def _next_receipt_number(db: AsyncSession, store_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count(PurchaseReceipt.id)).where(PurchaseReceipt.store_id == store_id)
    )
    count = result.scalar() or 0
    return f"GRN-{count + 1:04d}"


async def receive_purchase(
    db: AsyncSession, payload: PurchaseReceiptCreate, received_by: uuid.UUID | None = None
) -> PurchaseReceipt:
    """Create a goods receipt and update stock levels + PO received quantities."""
    receipt_id = uuid.uuid4()
    receipt_lines = []

    for line in payload.lines:
        receipt_lines.append(
            PurchaseReceiptLine(
                id=uuid.uuid4(),
                receipt_id=receipt_id,
                po_line_id=line.po_line_id,
                item_id=line.item_id,
                quantity_received=line.quantity_received,
                unit_cost=float(line.unit_cost),
                location_id=line.location_id,
            )
        )

        # Update PO line received_quantity
        po_line_result = await db.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.id == line.po_line_id)
        )
        po_line = po_line_result.scalar_one_or_none()
        if po_line:
            po_line.received_quantity += line.quantity_received

        # Update stock level
        stock_result = await db.execute(
            select(StockLevel).where(
                StockLevel.item_id == line.item_id,
                StockLevel.location_id == line.location_id,
            )
        )
        stock = stock_result.scalar_one_or_none()
        if stock:
            stock.quantity += line.quantity_received
        else:
            db.add(
                StockLevel(
                    id=uuid.uuid4(),
                    item_id=line.item_id,
                    location_id=line.location_id,
                    quantity=line.quantity_received,
                )
            )

    receipt = PurchaseReceipt(
        id=receipt_id,
        purchase_order_id=payload.purchase_order_id,
        store_id=payload.store_id,
        receipt_number=await _next_receipt_number(db, payload.store_id),
        received_by=received_by,
        notes=payload.notes,
    )
    db.add(receipt)
    db.add_all(receipt_lines)
    await db.flush()
    return receipt
