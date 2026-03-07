"""
Tax and city ledger models.

- TaxGroup: grouping of tax rates (e.g., GST = CGST + SGST).
- TaxRule: individual tax rate within a group.
- CityLedgerAccount: accounts receivable for corporate/house accounts.
- CityLedgerTransaction: charges and settlements against a ledger account.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaxGroup(Base):
    __tablename__ = "tax_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)  # e.g., "GST 5%", "GST 18%"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rules = relationship("TaxRule", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tax_groups_store_id", "store_id"),
    )


class TaxRule(Base):
    """Individual tax component within a group (e.g., CGST 2.5%)."""
    __tablename__ = "tax_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # CGST, SGST, IGST, VAT
    rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    group = relationship("TaxGroup", back_populates="rules")

    __table_args__ = (
        Index("ix_tax_rules_group_id", "group_id"),
    )


class CityLedgerAccount(Base):
    """Accounts receivable / house accounts for corporate clients."""
    __tablename__ = "city_ledger_accounts"

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
    credit_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    transactions = relationship("CityLedgerTransaction", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_city_ledger_accounts_store_id", "store_id"),
    )


class CityLedgerTransaction(Base):
    """Charges and settlements against a city ledger account."""
    __tablename__ = "city_ledger_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("city_ledger_accounts.id", ondelete="CASCADE"), nullable=False
    )
    # charge | settlement
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # For charges: link to order
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    account = relationship("CityLedgerAccount", back_populates="transactions")

    __table_args__ = (
        Index("ix_cl_transactions_account_id", "account_id"),
    )
