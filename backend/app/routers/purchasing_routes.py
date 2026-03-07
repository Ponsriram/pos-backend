"""
Purchasing routes – vendors, purchase orders, receipts.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.purchasing import Vendor, PurchaseOrder
from app.models.users import User
from app.schemas.purchasing_schema import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
    PurchaseOrderResponse,
    PurchaseReceiptCreate,
    PurchaseReceiptResponse,
)
from app.services.purchasing_service import (
    create_vendor,
    update_vendor,
    create_purchase_order,
    get_purchase_order,
    receive_purchase,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/purchasing", tags=["Purchasing"])


# ── Vendors ───────────────────────────────────────────────────────────────

@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def api_create_vendor(
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await create_vendor(db, payload)


@router.get("/vendors", response_model=list[VendorResponse])
async def api_list_vendors(
    store_id: UUID = Query(...),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Vendor).where(Vendor.store_id == store_id)
    if active_only:
        q = q.where(Vendor.is_active.is_(True))
    q = q.order_by(Vendor.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/vendors/{vendor_id}", response_model=VendorResponse)
async def api_update_vendor(
    vendor_id: UUID,
    payload: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return await update_vendor(db, vendor, payload)


# ── Purchase Orders ───────────────────────────────────────────────────────

@router.post("/orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def api_create_po(
    payload: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await create_purchase_order(db, payload, created_by=current_user.id)
    return await get_purchase_order(db, po.id)


@router.get("/orders", response_model=list[PurchaseOrderResponse])
async def api_list_pos(
    store_id: UUID = Query(...),
    po_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.store_id == store_id)
    )
    if po_status:
        q = q.where(PurchaseOrder.status == po_status)
    q = q.order_by(PurchaseOrder.created_at.desc())
    result = await db.execute(q)
    return result.scalars().unique().all()


@router.get("/orders/{po_id}", response_model=PurchaseOrderResponse)
async def api_get_po(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    po = await get_purchase_order(db, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    return po


@router.put("/orders/{po_id}/status", response_model=PurchaseOrderResponse)
async def api_update_po_status(
    po_id: UUID,
    payload: PurchaseOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    po = await get_purchase_order(db, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    po.status = payload.status
    await db.flush()
    return po


# ── Purchase Receipts ─────────────────────────────────────────────────────

@router.post("/receipts", response_model=PurchaseReceiptResponse, status_code=status.HTTP_201_CREATED)
async def api_receive_purchase(
    payload: PurchaseReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await receive_purchase(db, payload, received_by=current_user.id)
