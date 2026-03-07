"""
Marketing models – email campaigns and guest segmentation.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Boolean, DateTime, ForeignKey, Index, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Target segment: all | frequent | inactive | custom
    target_segment: Mapped[str] = mapped_column(String(30), nullable=False, default="all")
    # Custom filter criteria as JSON
    segment_filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # draft | scheduled | sent | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_recipients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_clicked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_campaigns_store_id", "store_id"),
        Index("ix_campaigns_status", "status"),
    )
