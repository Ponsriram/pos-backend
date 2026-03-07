"""
Pydantic schemas for Order, OrderItem, Payment, Sync, and Analytics endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Order Item ────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(1, ge=1)
    price: float = Field(..., ge=0, examples=[299.00])
    notes: str | None = None


class OrderItemUpdate(BaseModel):
    quantity: int | None = Field(None, ge=1)
    price: float | None = Field(None, ge=0)
    notes: str | None = None
    status: str | None = None  # active | cancelled


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    product_id: UUID | None
    quantity: int
    price: float
    tax_amount: float
    discount_amount: float
    total: float
    status: str
    notes: str | None
    kitchen_status: str | None
    cancel_reason: str | None

    model_config = {"from_attributes": True}


# ── Order ─────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    store_id: UUID
    employee_id: UUID | None = None
    terminal_id: UUID | None = None
    table_id: UUID | None = None
    guest_id: UUID | None = None
    shift_id: UUID | None = None
    order_type: str = Field("dine_in", examples=["dine_in", "takeaway", "delivery"])
    channel: str = Field("pos", examples=["pos", "online", "aggregator"])
    discount_amount: float = Field(0.0, ge=0)
    service_charge: float = Field(0.0, ge=0)
    notes: str | None = None
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    """Update an open order: items, discounts, notes."""
    employee_id: UUID | None = None
    table_id: UUID | None = None
    guest_id: UUID | None = None
    discount_amount: float | None = Field(None, ge=0)
    service_charge: float | None = Field(None, ge=0)
    notes: str | None = None
    # Items to add
    add_items: list[OrderItemCreate] | None = None
    # Items to update (by item id)
    update_items: list["OrderItemUpdateWithId"] | None = None
    # Item IDs to remove
    remove_item_ids: list[UUID] | None = None


class OrderItemUpdateWithId(BaseModel):
    id: UUID
    quantity: int | None = Field(None, ge=1)
    price: float | None = Field(None, ge=0)
    notes: str | None = None


class OrderResponse(BaseModel):
    id: UUID
    store_id: UUID
    employee_id: UUID | None
    terminal_id: UUID | None
    table_id: UUID | None
    guest_id: UUID | None
    shift_id: UUID | None
    order_number: str | None
    order_type: str
    status: str
    channel: str
    gross_amount: float
    tax_amount: float
    discount_amount: float
    service_charge: float
    tip_amount: float
    net_amount: float
    payment_status: str
    notes: str | None
    cancel_reason: str | None
    device_id: str | None
    sync_status: str | None
    created_at: datetime
    updated_at: datetime | None
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderComplete(BaseModel):
    """Mark an order as completed."""
    payment_status: str = Field("completed", examples=["completed"])


class OrderStatusUpdate(BaseModel):
    """Move an order through its lifecycle."""
    status: str = Field(..., examples=["in_kitchen", "ready", "served", "completed"])


class OrderCancelRequest(BaseModel):
    reason: str = Field(..., max_length=255, examples=["Customer changed mind"])


class OrderTransferRequest(BaseModel):
    """Transfer an order to a different table or waiter."""
    table_id: UUID | None = None
    employee_id: UUID | None = None


# ── Payment ───────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    order_id: UUID
    payment_method: str = Field(..., examples=["cash", "card", "upi", "wallet", "gift_card"])
    amount: float = Field(..., gt=0, examples=[500.00])
    tip_amount: float = Field(0.0, ge=0)
    reference: str | None = Field(None, max_length=255)


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    payment_method: str
    amount: float
    tip_amount: float
    reference: str | None
    is_refund: bool
    paid_at: datetime
    device_id: str | None
    sync_status: str | None

    model_config = {"from_attributes": True}


class RefundRequest(BaseModel):
    payment_id: UUID
    amount: float = Field(..., gt=0)
    reason: str = Field(..., max_length=255)


# ── Sync (offline POS → server) ──────────────────────────────────────────

class SyncOrderItem(BaseModel):
    product_id: UUID
    quantity: int = Field(1, ge=1)
    price: float = Field(..., ge=0)


class SyncOrder(BaseModel):
    """An order originating from an offline POS device."""
    device_id: str = Field(..., max_length=255)
    store_id: UUID
    employee_id: UUID | None = None
    terminal_id: UUID | None = None
    table_id: UUID | None = None
    order_type: str = "dine_in"
    discount_amount: float = 0.0
    items: list[SyncOrderItem] = Field(..., min_length=1)
    created_at: datetime  # original creation time on device


class SyncOrdersRequest(BaseModel):
    orders: list[SyncOrder] = Field(..., min_length=1)


class SyncPayment(BaseModel):
    """A payment recorded offline on a POS device."""
    device_id: str = Field(..., max_length=255)
    order_id: UUID
    payment_method: str
    amount: float = Field(..., gt=0)
    paid_at: datetime


class SyncPaymentsRequest(BaseModel):
    payments: list[SyncPayment] = Field(..., min_length=1)


class SyncResponse(BaseModel):
    synced: int
    failed: int
    errors: list[str] = []


# ── Analytics ─────────────────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_revenue: float
    total_orders: int
    tax_collected: float
    gross_sales: float
    net_sales: float
    total_discounts: float
    payment_breakdown: dict[str, float]
