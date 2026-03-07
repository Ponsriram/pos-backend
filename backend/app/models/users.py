"""
User model – represents a restaurant owner / admin.

Each user can own multiple stores. Authentication is done via
email + hashed password with JWT tokens.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Role: owner | manager | supervisor | cashier | waiter | kitchen | accountant | admin
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="owner")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    stores = relationship("Store", back_populates="owner", cascade="all, delete-orphan")
    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserPermission(Base):
    """Fine-grained permission assignments per user."""
    __tablename__ = "user_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    # e.g. orders.cancel, discounts.approve, reports.view, inventory.adjust
    permission: Mapped[str] = mapped_column(String(100), nullable=False)
    # Optional store scope – NULL means all stores
    store_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    user = relationship("User", back_populates="permissions")

    __table_args__ = (
        Index("ix_user_permissions_user_id", "user_id"),
    )
