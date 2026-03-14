"""
Order, Payment, and Sync routes.

POST   /orders                    → create order
GET    /orders                    → list orders (store_id, filters)
GET    /orders/{id}               → get single order
PUT    /orders/{id}               → update order (add/remove items)
PUT    /orders/{id}/status        → advance order status
PUT    /orders/{id}/cancel        → cancel order
PUT    /orders/{id}/transfer      → transfer table/waiter
POST   /orders/payments           → record a payment
PUT    /orders/payments/{id}      → edit a payment
POST   /orders/payments/refund    → issue refund
POST   /sync/orders               → bulk-sync offline orders
POST   /sync/payments             → bulk-sync offline payments
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orders import Order, Payment
from app.models.billing import KOT
from app.models.users import User
from app.schemas.order_schema import (
    OrderCreate,
    OrderResponse,
    OrderItemResponse,
    OrderStatusUpdate,
    OrderCancelRequest,
    OrderTransferRequest,
    OrderAddItemRequest,
    OrderUpdateItemRequest,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    RefundRequest,
    SyncOrdersRequest,
    SyncPaymentsRequest,
    SyncResponse,
)
from app.schemas.billing_schema import KOTResponse
from app.services.order_service import (
    create_order,
    update_order_status,
    cancel_order,
    transfer_order,
    add_order_item,
    update_order_item,
    delete_order_item,
    create_payment,
    update_payment,
    create_refund,
)
from app.services.billing_service import create_kot, get_kot
from app.services.sync_service import sync_orders, sync_payments
from app.utils.auth import get_current_user

router = APIRouter(tags=["Orders"])


# ── Create order ──────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order with line items",
)
async def api_create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    order = await create_order(db, payload)
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    return result.scalar_one()


# ── Get single order ─────────────────────────────────────────────────────

@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get a single order by ID",
)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get(
    "/orders/{order_id}/payments",
    response_model=list[PaymentResponse],
    summary="List payments recorded for an order",
)
async def get_order_payments(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    order_result = await db.execute(select(Order.id).where(Order.id == order_id))
    if not order_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await db.execute(
        select(Payment)
        .where(Payment.order_id == order_id)
        .order_by(Payment.paid_at.desc())
    )
    return result.scalars().all()


# ── List orders ───────────────────────────────────────────────────────────

@router.get(
    "/orders",
    response_model=list[OrderResponse],
    summary="List orders for a store with optional filters",
)
async def list_orders(
    store_id: UUID = Query(...),
    payment_status: str | None = Query(None),
    order_status: str | None = Query(None, alias="status"),
    order_type: str | None = Query(None),
    channel: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.store_id == store_id)
    )
    if payment_status:
        query = query.where(Order.payment_status == payment_status)
    if order_status:
        query = query.where(Order.status == order_status)
    if order_type:
        query = query.where(Order.order_type == order_type)
    if channel:
        query = query.where(Order.channel == channel)
    query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().unique().all()


# ── Update order status ──────────────────────────────────────────────────

@router.put(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Advance order through its lifecycle",
)
async def api_update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        order = await update_order_status(db, order, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return order


# ── Cancel order ──────────────────────────────────────────────────────────

@router.put(
    "/orders/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel an order",
)
async def api_cancel_order(
    order_id: UUID,
    payload: OrderCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        order = await cancel_order(db, order, payload.reason, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return order


# ── Transfer order ────────────────────────────────────────────────────────

@router.put(
    "/orders/{order_id}/transfer",
    response_model=OrderResponse,
    summary="Transfer order to another table or waiter",
)
async def api_transfer_order(
    order_id: UUID,
    payload: OrderTransferRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = await transfer_order(db, order, payload)
    return order


# ── Add item to order ─────────────────────────────────────────────────────

@router.post(
    "/orders/{order_id}/items",
    response_model=OrderItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to an existing order",
)
async def api_add_order_item(
    order_id: UUID,
    payload: OrderAddItemRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        item = await add_order_item(db, order, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return item


# ── Update order item ────────────────────────────────────────────────────

@router.put(
    "/orders/{order_id}/items/{item_id}",
    response_model=OrderItemResponse,
    summary="Update quantity or notes of an order item",
)
async def api_update_order_item(
    order_id: UUID,
    item_id: UUID,
    payload: OrderUpdateItemRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        item = await update_order_item(db, order, item_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return item


# ── Delete order item ────────────────────────────────────────────────────

@router.delete(
    "/orders/{order_id}/items/{item_id}",
    response_model=OrderItemResponse,
    summary="Remove an item from an order (before it is sent to kitchen)",
)
async def api_delete_order_item(
    order_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        item = await delete_order_item(db, order, item_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return item


# ── Create KOT (send items to kitchen) ───────────────────────────────────

@router.post(
    "/orders/{order_id}/kot",
    response_model=KOTResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send unsent order items to kitchen as a new KOT",
)
async def api_create_order_kot(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Resolve store_id from the order
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        kot = await create_kot(db, order_id, order.store_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_kot(db, kot.id)


# ── Payment ───────────────────────────────────────────────────────────────

@router.post(
    "/orders/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a payment for an order",
)
async def api_create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    order_result = await db.execute(select(Order).where(Order.id == payload.order_id))
    if not order_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        return await create_payment(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/orders/payments/{payment_id}",
    response_model=PaymentResponse,
    summary="Edit a payment for correction",
)
async def api_update_payment(
    payment_id: UUID,
    payload: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await update_payment(db, payment_id, payload)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ── Refund ────────────────────────────────────────────────────────────────

@router.post(
    "/orders/payments/refund",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a refund against a payment",
)
async def api_create_refund(
    payload: RefundRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await create_refund(db, payload)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ── Sync: offline orders ─────────────────────────────────────────────────

@router.post(
    "/sync/orders",
    response_model=SyncResponse,
    summary="Bulk-sync orders from an offline POS device",
)
async def api_sync_orders(
    payload: SyncOrdersRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await sync_orders(db, payload.orders)


# ── Sync: offline payments ───────────────────────────────────────────────

@router.post(
    "/sync/payments",
    response_model=SyncResponse,
    summary="Bulk-sync payments from an offline POS device",
)
async def api_sync_payments(
    payload: SyncPaymentsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await sync_payments(db, payload.payments)
