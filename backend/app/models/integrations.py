"""
Delivery aggregator integration models (Zomato, Swiggy, etc.).

- AggregatorConfig: platform-level aggregator definitions.
- AggregatorStoreLink: per-store aggregator credentials and config.
- AggregatorOrder: maps external orders to internal orders.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AggregatorConfig(Base):
    """Platform-level aggregator definition."""
    __tablename__ = "aggregator_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # zomato | swiggy | uber_eats | other
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    webhook_secret_header: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    store_links = relationship("AggregatorStoreLink", back_populates="aggregator")


class AggregatorStoreLink(Base):
    """Per-store credentials and configuration for an aggregator."""
    __tablename__ = "aggregator_store_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    aggregator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aggregator_configs.id", ondelete="CASCADE"), nullable=False
    )
    external_store_id: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_secret: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Arbitrary config JSON (menu sync url, etc.)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    aggregator = relationship("AggregatorConfig", back_populates="store_links")

    __table_args__ = (
        Index("ix_agg_store_links_store_id", "store_id"),
        Index("ix_agg_store_links_aggregator_id", "aggregator_id"),
    )


class AggregatorOrder(Base):
    """Maps external aggregator orders to internal orders."""
    __tablename__ = "aggregator_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    aggregator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aggregator_configs.id", ondelete="CASCADE"), nullable=False
    )
    # External order reference (idempotency key)
    external_order_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Internal order reference (created when we process the webhook)
    internal_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    # External status mirror
    external_status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    # Raw payload from the aggregator
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_agg_orders_store_id", "store_id"),
        Index("ix_agg_orders_external_id", "aggregator_id", "external_order_id", unique=True),
    )
