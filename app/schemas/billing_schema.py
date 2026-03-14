"""Pydantic schemas for KOTs, Invoices, and Bill Templates."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── KOT ───────────────────────────────────────────────────────────────────

class KOTItemResponse(BaseModel):
    id: UUID
    kot_id: UUID
    order_item_id: UUID
    product_name: str
    quantity: int
    notes: str | None

    model_config = {"from_attributes": True}


class KOTCreate(BaseModel):
    order_id: UUID
    store_id: UUID
    kitchen_section: str | None = Field(None, max_length=100)
    item_ids: list[UUID] | None = Field(None, description="Order item IDs to include; omit to auto-select unsent items")


class KOTStatusUpdate(BaseModel):
    status: str = Field(..., examples=["preparing", "ready"])


class KOTResponse(BaseModel):
    id: UUID
    order_id: UUID
    store_id: UUID
    kot_number: int
    kitchen_section: str | None
    status: str
    reprint_count: int
    created_at: datetime
    items: list[KOTItemResponse] = []

    model_config = {"from_attributes": True}


# ── Invoice ───────────────────────────────────────────────────────────────

class InvoiceGenerateRequest(BaseModel):
    order_id: UUID


class InvoiceResponse(BaseModel):
    id: UUID
    order_id: UUID
    store_id: UUID
    invoice_number: str
    gross_amount: float
    tax_amount: float
    discount_amount: float
    service_charge: float
    net_amount: float
    tax_breakdown: dict | None
    issued_at: datetime

    model_config = {"from_attributes": True}


# ── Bill Template ─────────────────────────────────────────────────────────

class BillTemplateCreate(BaseModel):
    store_id: UUID
    template_type: str = Field("receipt", examples=["receipt", "kot", "invoice"])
    name: str = Field(..., max_length=200)
    language: str = Field("en", max_length=10)
    content: str = Field(..., description="Template body (HTML/text with placeholders)")
    header_text: str | None = None
    footer_text: str | None = None
    logo_url: str | None = Field(None, max_length=500)
    is_default: bool = False
    is_active: bool = True


class BillTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    language: str | None = Field(None, max_length=10)
    content: str | None = None
    header_text: str | None = None
    footer_text: str | None = None
    logo_url: str | None = Field(None, max_length=500)
    is_default: bool | None = None
    is_active: bool | None = None


class BillTemplateResponse(BaseModel):
    id: UUID
    store_id: UUID
    template_type: str
    name: str
    language: str
    content: str
    header_text: str | None
    footer_text: str | None
    logo_url: str | None
    is_default: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
