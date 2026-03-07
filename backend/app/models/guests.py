"""
Guest / customer engagement models.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Guest(Base):
    """Customer / guest profile."""
    __tablename__ = "guests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Preferences
    dietary_preference: Mapped[str | None] = mapped_column(String(30), nullable=True)  # veg | non_veg | vegan
    spice_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mild | medium | hot
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Visit tracking
    total_visits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_spend: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Loyalty
    loyalty_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_guests_store_id", "store_id"),
        Index("ix_guests_phone", "phone"),
        Index("ix_guests_email", "email"),
    )
