"""Pydantic schemas for Inventory, Stock, Recipe, and StockTransfer."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Inventory Unit ────────────────────────────────────────────────────────

class InventoryUnitCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=50, examples=["kg", "litre", "piece"])
    abbreviation: str = Field(..., max_length=10, examples=["kg", "l", "pc"])
    base_unit_id: UUID | None = None
    conversion_factor: float = 1.0


class InventoryUnitResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    abbreviation: str
    base_unit_id: UUID | None
    conversion_factor: float

    model_config = {"from_attributes": True}


# ── Inventory Location ───────────────────────────────────────────────────

class InventoryLocationCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=100, examples=["Main Kitchen", "Bar", "Walk-in Fridge"])
    description: str | None = None
    is_active: bool = True


class InventoryLocationResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Inventory Item ────────────────────────────────────────────────────────

class InventoryItemCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=200)
    sku: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    unit_id: UUID
    min_stock: float = 0
    max_stock: float | None = None
    reorder_level: float | None = None
    reorder_quantity: float | None = None
    preferred_vendor_id: UUID | None = None
    tags: list[str] | None = None
    is_active: bool = True


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    sku: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    unit_id: UUID | None = None
    min_stock: float | None = None
    max_stock: float | None = None
    reorder_level: float | None = None
    reorder_quantity: float | None = None
    preferred_vendor_id: UUID | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class InventoryItemResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    sku: str | None
    category: str | None
    unit_id: UUID
    min_stock: float
    max_stock: float | None
    reorder_level: float | None
    reorder_quantity: float | None
    last_purchase_price: float | None
    average_cost: float | None
    preferred_vendor_id: UUID | None
    tags: list[str] | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Stock Level ───────────────────────────────────────────────────────────

class StockLevelResponse(BaseModel):
    id: UUID
    item_id: UUID
    location_id: UUID
    quantity: float
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Stock Adjustment ─────────────────────────────────────────────────────

class StockAdjustmentCreate(BaseModel):
    store_id: UUID
    item_id: UUID
    location_id: UUID
    quantity_change: float = Field(..., examples=[10.0, -5.0])
    reason: str = Field(..., max_length=100, examples=["physical_count", "wastage", "production"])
    notes: str | None = None


class StockAdjustmentResponse(BaseModel):
    id: UUID
    store_id: UUID
    item_id: UUID
    location_id: UUID
    quantity_change: float
    reason: str
    notes: str | None
    adjusted_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Recipe ────────────────────────────────────────────────────────────────

class RecipeLineCreate(BaseModel):
    ingredient_id: UUID
    quantity: float = Field(..., gt=0)
    unit_id: UUID


class RecipeLineResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    ingredient_id: UUID
    quantity: float
    unit_id: UUID

    model_config = {"from_attributes": True}


class RecipeCreate(BaseModel):
    store_id: UUID
    product_id: UUID
    name: str = Field(..., max_length=200)
    description: str | None = None
    yield_quantity: float = 1.0
    wastage_percent: float = Field(0.0, ge=0, le=100)
    is_active: bool = True
    lines: list[RecipeLineCreate] = Field(..., min_length=1)


class RecipeUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    yield_quantity: float | None = None
    wastage_percent: float | None = Field(None, ge=0, le=100)
    is_active: bool | None = None
    lines: list[RecipeLineCreate] | None = None  # replaces all lines when provided


class RecipeResponse(BaseModel):
    id: UUID
    store_id: UUID
    product_id: UUID
    name: str
    description: str | None
    yield_quantity: float
    wastage_percent: float
    is_active: bool
    created_at: datetime
    lines: list[RecipeLineResponse] = []

    model_config = {"from_attributes": True}


# ── Stock Transfer ────────────────────────────────────────────────────────

class StockTransferLineCreate(BaseModel):
    item_id: UUID
    quantity: float = Field(..., gt=0)
    unit_id: UUID


class StockTransferLineResponse(BaseModel):
    id: UUID
    transfer_id: UUID
    item_id: UUID
    quantity: float
    received_quantity: float | None
    unit_id: UUID

    model_config = {"from_attributes": True}


class StockTransferCreate(BaseModel):
    from_store_id: UUID
    to_store_id: UUID
    notes: str | None = None
    lines: list[StockTransferLineCreate] = Field(..., min_length=1)


class StockTransferStatusUpdate(BaseModel):
    status: str = Field(..., examples=["approved", "shipped", "received", "cancelled"])


class StockTransferResponse(BaseModel):
    id: UUID
    from_store_id: UUID
    to_store_id: UUID
    status: str
    notes: str | None
    requested_by: UUID | None
    approved_by: UUID | None
    created_at: datetime
    lines: list[StockTransferLineResponse] = []

    model_config = {"from_attributes": True}
