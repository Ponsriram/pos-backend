"""
Delivery models – delivery order details and tracking.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Numeric, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryOrderDetails(Base):
    """Delivery-specific details for an order."""
    __tablename__ = "delivery_order_details"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Customer info
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    landmark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # own_delivery | aggregator | third_party
    delivery_type: Mapped[str] = mapped_column(String(20), nullable=False, default="own_delivery")
    # pending | assigned | out_for_delivery | delivered | failed | returned
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")

    # Assigned delivery staff
    delivery_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    delivery_charge: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    estimated_delivery_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_delivery_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Proof of delivery
    proof_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    order = relationship("Order")

    __table_args__ = (
        Index("ix_delivery_details_order_id", "order_id"),
        Index("ix_delivery_details_status", "delivery_status"),
        Index("ix_delivery_details_employee", "delivery_employee_id"),
    )
