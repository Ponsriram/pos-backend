"""
Order, OrderItem, and Payment models.

Orders hold a snapshot of totals; items track individual line items.
Payments record how each order was settled (cash / card / UPI / wallet / etc.).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Order ─────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    terminal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_terminals.id", ondelete="SET NULL"), nullable=True
    )
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Link to guest profile
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True
    )
    # Link to shift
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True
    )

    # Order number for display (unique per store per day)
    order_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # dine_in | takeaway | delivery | aggregator
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, default="dine_in")
    # Order status lifecycle:
    # open -> sent_to_kitchen -> preparing -> ready ->
    #   dine_in: served -> completed
    #   takeaway: handed_over -> completed
    #   delivery/aggregator: out_for_delivery -> delivered -> completed
    # and then payment can move completed -> paid
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    # Channel: pos | online | aggregator
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="pos")

    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    service_charge: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tip_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # pending | partial | completed | refunded
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # City ledger posting
    ledger_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("city_ledger_accounts.id", ondelete="SET NULL"), nullable=True
    )

    # Sync tracking
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    store = relationship("Store", back_populates="orders")
    employee = relationship("Employee", back_populates="orders")
    terminal = relationship("POSTerminal", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    kots = relationship("KOT", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_orders_store_id", "store_id"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_payment_status", "payment_status"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_store_date", "store_id", "created_at"),
        Index("ix_orders_guest_id", "guest_id"),
    )


# ── OrderItem ─────────────────────────────────────────────────────────────

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Snapshot of product name at the time of ordering
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # Item-level status: active | cancelled | voided
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # KOT tracking
    kot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kots.id", ondelete="SET NULL"), nullable=True
    )
    # Kitchen status: pending | sent | preparing | ready | served
    kitchen_status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="pending")

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_status", "status"),
    )


# ── Payment ───────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    # cash | card | upi | wallet | gift_card | coupon | loyalty | city_ledger
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tip_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # For refunds: link to original payment
    is_refund: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )

    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Sync tracking
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    order = relationship("Order", back_populates="payments")

    __table_args__ = (
        Index("ix_payments_order_id", "order_id"),
        Index("ix_payments_method", "payment_method"),
    )
