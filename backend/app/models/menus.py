"""
Menu models – support multiple menus per store with scheduling and pricing.

- Menu: named menu with validity windows.
- MenuItem: links Product to a menu with display overrides.
- MenuSchedule: day/time windows for menu availability.
"""

import uuid
from datetime import datetime, date, time, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, Date, Time,
    ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # breakfast | lunch | dinner | bar | seasonal | all_day
    menu_type: Mapped[str] = mapped_column(String(30), nullable=False, default="all_day")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Validity window
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Channel applicability: ["dine_in", "takeaway", "delivery", "aggregator"]
    channels: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    items = relationship("MenuItem", back_populates="menu", cascade="all, delete-orphan")
    schedules = relationship("MenuSchedule", back_populates="menu", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_menus_store_id", "store_id"),
    )


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    # Display overrides
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Menu-specific pricing (NULL = use product default)
    price_override: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    tax_percent_override: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Tags: veg, non_veg, spicy, gluten_free, etc.
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    menu = relationship("Menu", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        Index("ix_menu_items_menu_id", "menu_id"),
        Index("ix_menu_items_product_id", "product_id"),
    )


class MenuSchedule(Base):
    """Day/time schedule when a menu is available."""
    __tablename__ = "menu_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False
    )
    # 0=Monday .. 6=Sunday
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    menu = relationship("Menu", back_populates="schedules")

    __table_args__ = (
        Index("ix_menu_schedules_menu_id", "menu_id"),
    )


class MenuPricingRule(Base):
    """Channel/time-based pricing rules for menu items.

    Supports happy hour, day-of-week, outlet-level, and channel-based pricing.
    """
    __tablename__ = "menu_pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Rule type: happy_hour | day_of_week | channel | combo
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Channel filter (NULL = all)
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Day of week filter (NULL = all)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Pricing: either fixed price or percentage discount
    fixed_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_menu_pricing_rules_store_id", "store_id"),
        Index("ix_menu_pricing_rules_product_id", "product_id"),
    )
