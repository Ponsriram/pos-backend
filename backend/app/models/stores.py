"""
Store-related models.

- Store: a physical restaurant location owned by a User.
- Chain: restaurant chain / brand grouping.
- POSTerminal: a device registered at a store (tablet / kiosk).
- Employee: staff member assigned to a store.
- DineInTable: physical tables inside a store.
- OrderTableLink: many-to-many for table merges.
- Expense: operational expense ledger per store.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Chain / Brand ─────────────────────────────────────────────────────────

class Chain(Base):
    """Restaurant chain or brand grouping multiple outlets."""
    __tablename__ = "chains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    stores = relationship("Store", back_populates="chain")

    __table_args__ = (
        Index("ix_chains_owner_id", "owner_id"),
    )


# ── Store ─────────────────────────────────────────────────────────────────

class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chain_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chains.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    owner = relationship("User", back_populates="stores")
    chain = relationship("Chain", back_populates="stores")
    terminals = relationship("POSTerminal", back_populates="store", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="store", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="store", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    tables = relationship("DineInTable", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="store", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_stores_owner_id", "owner_id"),
        Index("ix_stores_chain_id", "chain_id"),
    )

    def __repr__(self) -> str:
        return f"<Store {self.name}>"


# ── POS Terminal ──────────────────────────────────────────────────────────

class POSTerminal(Base):
    __tablename__ = "pos_terminals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    device_name: Mapped[str] = mapped_column(String(120), nullable=False)
    device_identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    store = relationship("Store", back_populates="terminals")
    orders = relationship("Order", back_populates="terminal")

    __table_args__ = (
        Index("ix_pos_terminals_store_id", "store_id"),
        Index("ix_pos_terminals_device_identifier", "device_identifier"),
    )


# ── Employee ──────────────────────────────────────────────────────────────

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    employee_code: Mapped[str] = mapped_column(String(20), nullable=False)
    pin: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="cashier")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    store = relationship("Store", back_populates="employees")
    orders = relationship("Order", back_populates="employee")

    __table_args__ = (
        Index("ix_employees_store_id", "store_id"),
        Index("ix_employees_user_id", "user_id"),
    )


# ── Dine-In Table ────────────────────────────────────────────────────────

class DineInTable(Base):
    __tablename__ = "dine_in_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    store = relationship("Store", back_populates="tables")
    orders = relationship("Order", back_populates="table")

    __table_args__ = (
        Index("ix_dine_in_tables_store_id", "store_id"),
        Index("ix_dine_in_tables_status", "status"),
    )


# ── Table Merge (many-to-many: order ↔ tables) ──────────────────────────

class OrderTableLink(Base):
    """Links multiple tables to a single order (table merge)."""
    __tablename__ = "order_table_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dine_in_tables.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_order_table_links_order_id", "order_id"),
        Index("ix_order_table_links_table_id", "table_id"),
    )


# ── Expense ───────────────────────────────────────────────────────────────

class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    store = relationship("Store", back_populates="expenses")

    __table_args__ = (
        Index("ix_expenses_store_id", "store_id"),
    )
