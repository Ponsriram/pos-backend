"""Pydantic schemas for Shifts and Day-Close."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Shift ─────────────────────────────────────────────────────────────────

class ShiftOpen(BaseModel):
    store_id: UUID
    terminal_id: UUID | None = None
    employee_id: UUID
    opening_cash: float = Field(0.0, ge=0)
    notes: str | None = None


class ShiftClose(BaseModel):
    closing_cash: float = Field(..., ge=0)
    notes: str | None = None
    payment_summaries: list["ShiftPaymentSummaryCreate"] | None = None


class ShiftPaymentSummaryCreate(BaseModel):
    payment_method: str = Field(..., max_length=30, examples=["cash", "card", "upi"])
    expected_amount: float = Field(0.0, ge=0)
    actual_amount: float = Field(0.0, ge=0)


class ShiftPaymentSummaryResponse(BaseModel):
    id: UUID
    shift_id: UUID
    payment_method: str
    expected_amount: float
    actual_amount: float
    variance: float

    model_config = {"from_attributes": True}


class ShiftResponse(BaseModel):
    id: UUID
    store_id: UUID
    terminal_id: UUID | None
    employee_id: UUID
    status: str
    opening_cash: float
    closing_cash: float | None
    expected_cash: float | None
    cash_variance: float | None
    total_sales: float
    total_orders: int
    notes: str | None
    started_at: datetime
    ended_at: datetime | None
    payment_summaries: list[ShiftPaymentSummaryResponse] = []

    model_config = {"from_attributes": True}


# ── Day Close ─────────────────────────────────────────────────────────────

class DayCloseCreate(BaseModel):
    store_id: UUID
    business_date: date


class DayCloseResponse(BaseModel):
    id: UUID
    store_id: UUID
    business_date: date
    total_orders: int
    gross_sales: float
    total_tax: float
    total_discounts: float
    total_service_charge: float
    total_tips: float
    net_sales: float
    total_expenses: float
    net_cash: float
    payment_breakdown: dict | None
    order_type_breakdown: dict | None
    cancelled_orders: int
    closed_by: UUID | None
    closed_at: datetime

    model_config = {"from_attributes": True}
