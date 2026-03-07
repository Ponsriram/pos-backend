"""Pydantic schemas for Vendors, Purchase Orders, and Purchase Receipts."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Vendor ────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=200)
    address: str | None = None
    gst_number: str | None = Field(None, max_length=50)
    payment_terms_days: int = Field(0, ge=0)


class VendorUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=200)
    address: str | None = None
    gst_number: str | None = Field(None, max_length=50)
    payment_terms_days: int | None = Field(None, ge=0)
    is_active: bool | None = None


class VendorResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None
    gst_number: str | None
    payment_terms_days: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Purchase Order ────────────────────────────────────────────────────────

class PurchaseOrderLineCreate(BaseModel):
    item_id: UUID
    quantity: float = Field(..., gt=0)
    unit_id: UUID
    unit_price: float = Field(..., ge=0)


class PurchaseOrderLineResponse(BaseModel):
    id: UUID
    purchase_order_id: UUID
    item_id: UUID
    quantity: float
    unit_id: UUID
    unit_price: float
    total_price: float
    received_quantity: float

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    store_id: UUID
    vendor_id: UUID
    notes: str | None = None
    expected_delivery: date | None = None
    lines: list[PurchaseOrderLineCreate] = Field(..., min_length=1)


class PurchaseOrderStatusUpdate(BaseModel):
    status: str = Field(..., examples=["ordered", "cancelled"])


class PurchaseOrderResponse(BaseModel):
    id: UUID
    store_id: UUID
    vendor_id: UUID
    po_number: str
    status: str
    total_amount: float
    notes: str | None
    ordered_at: datetime | None
    expected_delivery: date | None
    created_by: UUID | None
    created_at: datetime
    lines: list[PurchaseOrderLineResponse] = []

    model_config = {"from_attributes": True}


# ── Purchase Receipt ─────────────────────────────────────────────────────

class PurchaseReceiptLineCreate(BaseModel):
    po_line_id: UUID
    item_id: UUID
    quantity_received: float = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)
    location_id: UUID


class PurchaseReceiptLineResponse(BaseModel):
    id: UUID
    receipt_id: UUID
    po_line_id: UUID
    item_id: UUID
    quantity_received: float
    unit_cost: float
    location_id: UUID

    model_config = {"from_attributes": True}


class PurchaseReceiptCreate(BaseModel):
    purchase_order_id: UUID
    store_id: UUID
    notes: str | None = None
    lines: list[PurchaseReceiptLineCreate] = Field(..., min_length=1)


class PurchaseReceiptResponse(BaseModel):
    id: UUID
    purchase_order_id: UUID
    store_id: UUID
    receipt_number: str
    received_by: UUID | None
    notes: str | None
    created_at: datetime
    lines: list[PurchaseReceiptLineResponse] = []

    model_config = {"from_attributes": True}
