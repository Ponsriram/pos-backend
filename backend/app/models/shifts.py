"""
Shift management and day close models.

- Shift: cashier shift per terminal.
- ShiftPaymentSummary: per-payment-method totals for a shift.
- DayClose: end-of-day aggregated totals per store.
"""

import uuid
from datetime import datetime, date, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, Date, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    terminal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_terminals.id", ondelete="SET NULL"), nullable=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    # open | closed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    opening_cash: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    closing_cash: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Expected cash based on transactions
    expected_cash: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cash_variance: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_sales: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment_summaries = relationship("ShiftPaymentSummary", back_populates="shift", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_shifts_store_id", "store_id"),
        Index("ix_shifts_employee_id", "employee_id"),
        Index("ix_shifts_status", "status"),
        Index("ix_shifts_started_at", "started_at"),
    )


class ShiftPaymentSummary(Base):
    """Per payment method totals for a shift."""
    __tablename__ = "shift_payment_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False
    )
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    actual_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    variance: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    shift = relationship("Shift", back_populates="payment_summaries")

    __table_args__ = (
        Index("ix_shift_pay_summary_shift_id", "shift_id"),
    )


class DayClose(Base):
    """End-of-day summary per store per business date."""
    __tablename__ = "day_closes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Aggregated totals
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gross_sales: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_discounts: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_service_charge: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_tips: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_sales: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_expenses: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_cash: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    # Payment method breakdown as JSON
    payment_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Order type breakdown as JSON
    order_type_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cancelled_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_day_closes_store_id", "store_id"),
        Index("ix_day_closes_business_date", "business_date"),
        Index("ix_day_closes_store_date", "store_id", "business_date", unique=True),
    )
