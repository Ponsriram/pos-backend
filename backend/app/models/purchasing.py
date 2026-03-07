"""
Purchasing models – vendors and purchase orders.

- Vendor: supplier for inventory items.
- PurchaseOrder / PurchaseOrderLine: order placed with vendor.
- PurchaseReceipt / PurchaseReceiptLine: goods received.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Payment terms in days (e.g., Net 30)
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")

    __table_args__ = (
        Index("ix_vendors_store_id", "store_id"),
    )


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False
    )
    po_number: Mapped[str] = mapped_column(String(50), nullable=False)
    # draft | ordered | received_partial | received_full | cancelled
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    vendor = relationship("Vendor", back_populates="purchase_orders")
    lines = relationship("PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan")
    receipts = relationship("PurchaseReceipt", back_populates="purchase_order")

    __table_args__ = (
        Index("ix_purchase_orders_store_id", "store_id"),
        Index("ix_purchase_orders_vendor_id", "vendor_id"),
        Index("ix_purchase_orders_status", "status"),
    )


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT"), nullable=False
    )
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    received_quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)

    purchase_order = relationship("PurchaseOrder", back_populates="lines")

    __table_args__ = (
        Index("ix_po_lines_po_id", "purchase_order_id"),
    )


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    receipt_number: Mapped[str] = mapped_column(String(50), nullable=False)
    received_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    purchase_order = relationship("PurchaseOrder", back_populates="receipts")
    lines = relationship("PurchaseReceiptLine", back_populates="receipt", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_purchase_receipts_po_id", "purchase_order_id"),
        Index("ix_purchase_receipts_store_id", "store_id"),
    )


class PurchaseReceiptLine(Base):
    __tablename__ = "purchase_receipt_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_receipts.id", ondelete="CASCADE"), nullable=False
    )
    po_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_lines.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity_received: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False
    )

    receipt = relationship("PurchaseReceipt", back_populates="lines")

    __table_args__ = (
        Index("ix_pr_lines_receipt_id", "receipt_id"),
    )
