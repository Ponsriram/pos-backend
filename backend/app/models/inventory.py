"""
Inventory, stock, recipe, and unit models.

- InventoryItem: raw material / ingredient.
- InventoryUnit: measurement units with conversion factors.
- InventoryLocation: storage areas within a store.
- StockLevel: current stock per item per location.
- StockAdjustment: manual corrections, wastage, shrinkage.
- Recipe / RecipeLine: link sellable products to ingredients.
- StockTransfer: inter-store stock movements.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Inventory Unit ────────────────────────────────────────────────────────

class InventoryUnit(Base):
    __tablename__ = "inventory_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # kg, g, l, ml, pcs, case
    abbreviation: Mapped[str] = mapped_column(String(10), nullable=False)
    # Base unit reference for conversions (NULL = this is a base unit)
    base_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="SET NULL"), nullable=True
    )
    # Conversion factor to base unit (e.g., 1 kg = 1000 g → factor = 1000)
    conversion_factor: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=1.0)

    __table_args__ = (
        Index("ix_inventory_units_store_id", "store_id"),
    )


# ── Inventory Location ───────────────────────────────────────────────────

class InventoryLocation(Base):
    __tablename__ = "inventory_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)  # Main Kitchen, Bar Store, Cold Room
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    stock_levels = relationship("StockLevel", back_populates="location", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_inventory_locations_store_id", "store_id"),
    )


# ── Inventory Item ────────────────────────────────────────────────────────

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT"), nullable=False
    )
    # Thresholds
    min_stock: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    max_stock: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    reorder_level: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    reorder_quantity: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # Cost tracking
    last_purchase_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    average_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Supplier reference
    preferred_vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    unit = relationship("InventoryUnit")
    stock_levels = relationship("StockLevel", back_populates="item", cascade="all, delete-orphan")
    recipe_lines = relationship("RecipeLine", back_populates="ingredient")

    __table_args__ = (
        Index("ix_inventory_items_store_id", "store_id"),
        Index("ix_inventory_items_category", "category"),
    )


# ── Stock Level ───────────────────────────────────────────────────────────

class StockLevel(Base):
    """Current stock quantity per item per location."""
    __tablename__ = "stock_levels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    item = relationship("InventoryItem", back_populates="stock_levels")
    location = relationship("InventoryLocation", back_populates="stock_levels")

    __table_args__ = (
        Index("ix_stock_levels_item_id", "item_id"),
        Index("ix_stock_levels_location_id", "location_id"),
        Index("ix_stock_levels_item_location", "item_id", "location_id", unique=True),
    )


# ── Stock Adjustment ─────────────────────────────────────────────────────

class StockAdjustment(Base):
    """Manual stock corrections: wastage, shrinkage, counting corrections."""
    __tablename__ = "stock_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False
    )
    # Positive = stock in, negative = stock out
    quantity_change: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    # wastage | shrinkage | correction | production | consumption | transfer_in | transfer_out
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    adjusted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    item = relationship("InventoryItem")

    __table_args__ = (
        Index("ix_stock_adjustments_store_id", "store_id"),
        Index("ix_stock_adjustments_item_id", "item_id"),
    )


# ── Recipe ────────────────────────────────────────────────────────────────

class Recipe(Base):
    """Links a sellable Product to its ingredient requirements."""
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Batch size: recipe produces this many portions
    yield_quantity: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=1)
    # Wastage percentage
    wastage_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    product = relationship("Product")
    lines = relationship("RecipeLine", back_populates="recipe", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_recipes_store_id", "store_id"),
        Index("ix_recipes_product_id", "product_id"),
    )


class RecipeLine(Base):
    __tablename__ = "recipe_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT"), nullable=False
    )

    recipe = relationship("Recipe", back_populates="lines")
    ingredient = relationship("InventoryItem", back_populates="recipe_lines")
    unit = relationship("InventoryUnit")

    __table_args__ = (
        Index("ix_recipe_lines_recipe_id", "recipe_id"),
    )


# ── Stock Transfer ───────────────────────────────────────────────────────

class StockTransfer(Base):
    """Inter-store stock transfer."""
    __tablename__ = "stock_transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    from_store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    to_store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    # requested | approved | shipped | received | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    lines = relationship("StockTransferLine", back_populates="transfer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_stock_transfers_from_store", "from_store_id"),
        Index("ix_stock_transfers_to_store", "to_store_id"),
    )


class StockTransferLine(Base):
    __tablename__ = "stock_transfer_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    received_quantity: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT"), nullable=False
    )

    transfer = relationship("StockTransfer", back_populates="lines")

    __table_args__ = (
        Index("ix_stock_transfer_lines_transfer_id", "transfer_id"),
    )
