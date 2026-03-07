"""Pydantic schemas for Tax, City Ledger, and Accounting."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Tax Group / Rule ──────────────────────────────────────────────────────

class TaxRuleCreate(BaseModel):
    name: str = Field(..., max_length=100, examples=["CGST", "SGST", "IGST"])
    rate: float = Field(..., ge=0, le=100, examples=[2.5, 9.0])


class TaxRuleResponse(BaseModel):
    id: UUID
    group_id: UUID
    name: str
    rate: float

    model_config = {"from_attributes": True}


class TaxGroupCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=100, examples=["GST 5%", "GST 18%"])
    description: str | None = None
    is_inclusive: bool = False
    rules: list[TaxRuleCreate] = Field(..., min_length=1)


class TaxGroupUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    is_inclusive: bool | None = None
    is_active: bool | None = None
    rules: list[TaxRuleCreate] | None = None  # replaces all rules when provided


class TaxGroupResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    description: str | None
    is_inclusive: bool
    is_active: bool
    created_at: datetime
    rules: list[TaxRuleResponse] = []

    model_config = {"from_attributes": True}


# ── City Ledger Account ──────────────────────────────────────────────────

class CityLedgerAccountCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=200)
    address: str | None = None
    gst_number: str | None = Field(None, max_length=50)
    credit_limit: float = Field(0.0, ge=0)


class CityLedgerAccountUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=200)
    address: str | None = None
    gst_number: str | None = Field(None, max_length=50)
    credit_limit: float | None = Field(None, ge=0)
    is_active: bool | None = None


class CityLedgerAccountResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None
    gst_number: str | None
    credit_limit: float
    current_balance: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── City Ledger Transaction ──────────────────────────────────────────────

class CityLedgerTransactionCreate(BaseModel):
    account_id: UUID
    transaction_type: str = Field(..., examples=["charge", "settlement"])
    amount: float = Field(..., gt=0)
    order_id: UUID | None = None
    description: str | None = Field(None, max_length=500)
    reference: str | None = Field(None, max_length=200)


class CityLedgerTransactionResponse(BaseModel):
    id: UUID
    account_id: UUID
    transaction_type: str
    amount: float
    order_id: UUID | None
    description: str | None
    reference: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
