"""
Billing models – KOT, invoices, and templates.

- KOT: Kitchen Order Ticket linked to order items.
- KOTItem: individual items on a KOT.
- Invoice: finalized bill with unique number.
- BillTemplate: configurable templates for KOTs and receipts.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KOT(Base):
    """Kitchen Order Ticket."""
    __tablename__ = "kots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    kot_number: Mapped[str] = mapped_column(String(30), nullable=False)
    # Target kitchen section
    kitchen_section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # printed | acknowledged | preparing | completed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="printed")
    reprint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    items = relationship("KOTItem", back_populates="kot", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_kots_order_id", "order_id"),
        Index("ix_kots_store_id", "store_id"),
    )


class KOTItem(Base):
    __tablename__ = "kot_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kots.id", ondelete="CASCADE"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    kot = relationship("KOT", back_populates="items")

    __table_args__ = (
        Index("ix_kot_items_kot_id", "kot_id"),
    )


class Invoice(Base):
    """Finalized bill / invoice for an order."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    # Snapshot of financials at time of billing
    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    service_charge: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # Tax breakdown JSON: [{"tax_name": "CGST", "rate": 2.5, "amount": 25.0}, ...]
    tax_breakdown: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_invoices_store_id", "store_id"),
        Index("ix_invoices_invoice_number", "invoice_number"),
    )


class BillTemplate(Base):
    """Configurable templates for KOTs, receipts, and bills."""
    __tablename__ = "bill_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    # kot | receipt | invoice | email_receipt | email_marketing
    template_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Language code (e.g., en, hi, ta)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    # Template content (HTML, text, or JSON structure)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Branding
    header_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_bill_templates_store_id", "store_id"),
        Index("ix_bill_templates_type", "template_type"),
    )
