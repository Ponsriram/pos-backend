"""Pydantic schemas for Menu, MenuItem, MenuSchedule, and MenuPricingRule."""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field


# ── Menu ──────────────────────────────────────────────────────────────────

class MenuCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=200)
    description: str | None = None
    menu_type: str = Field("regular", examples=["regular", "breakfast", "lunch", "dinner", "happy_hour"])
    is_active: bool = True
    valid_from: date | None = None
    valid_until: date | None = None
    channels: list[str] | None = None  # ["pos", "online", "aggregator"]
    sort_order: int = 0


class MenuUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    menu_type: str | None = None
    is_active: bool | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    channels: list[str] | None = None
    sort_order: int | None = None


class MenuResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    description: str | None
    menu_type: str
    is_active: bool
    valid_from: date | None
    valid_until: date | None
    channels: list[str] | None
    sort_order: int
    created_at: datetime
    items: list["MenuItemResponse"] = []
    schedules: list["MenuScheduleResponse"] = []

    model_config = {"from_attributes": True}


# ── Menu Item ─────────────────────────────────────────────────────────────

class MenuItemCreate(BaseModel):
    menu_id: UUID
    product_id: UUID
    display_name: str | None = Field(None, max_length=200)
    description_override: str | None = None
    price_override: float | None = Field(None, ge=0)
    tax_percent_override: float | None = Field(None, ge=0)
    sort_order: int = 0
    is_visible: bool = True
    is_available: bool = True
    tags: list[str] | None = None


class MenuItemUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=200)
    description_override: str | None = None
    price_override: float | None = Field(None, ge=0)
    tax_percent_override: float | None = Field(None, ge=0)
    sort_order: int | None = None
    is_visible: bool | None = None
    is_available: bool | None = None
    tags: list[str] | None = None


class MenuItemResponse(BaseModel):
    id: UUID
    menu_id: UUID
    product_id: UUID
    display_name: str | None
    description_override: str | None
    price_override: float | None
    tax_percent_override: float | None
    sort_order: int
    is_visible: bool
    is_available: bool
    tags: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Menu Schedule ─────────────────────────────────────────────────────────

class MenuScheduleCreate(BaseModel):
    menu_id: UUID
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday … 6=Sunday")
    start_time: time
    end_time: time


class MenuScheduleResponse(BaseModel):
    id: UUID
    menu_id: UUID
    day_of_week: int
    start_time: time
    end_time: time

    model_config = {"from_attributes": True}


# ── Menu Pricing Rule ────────────────────────────────────────────────────

class MenuPricingRuleCreate(BaseModel):
    store_id: UUID
    menu_item_id: UUID | None = None
    product_id: UUID | None = None
    name: str = Field(..., max_length=200)
    rule_type: str = Field(..., examples=["happy_hour", "combo", "channel_override", "time_based"])
    channel: str | None = None
    day_of_week: int | None = Field(None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    fixed_price: float | None = Field(None, ge=0)
    discount_percent: float | None = Field(None, ge=0, le=100)
    priority: int = 0
    is_active: bool = True


class MenuPricingRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    rule_type: str | None = None
    channel: str | None = None
    day_of_week: int | None = Field(None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    fixed_price: float | None = Field(None, ge=0)
    discount_percent: float | None = Field(None, ge=0, le=100)
    priority: int | None = None
    is_active: bool | None = None


class MenuPricingRuleResponse(BaseModel):
    id: UUID
    store_id: UUID
    menu_item_id: UUID | None
    product_id: UUID | None
    name: str
    rule_type: str
    channel: str | None
    day_of_week: int | None
    start_time: time | None
    end_time: time | None
    valid_from: date | None
    valid_until: date | None
    fixed_price: float | None
    discount_percent: float | None
    priority: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
