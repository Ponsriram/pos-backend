"""Pydantic schemas for Guest / CRM."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GuestCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=200)
    address: str | None = None
    dietary_preference: str | None = Field(None, max_length=100)
    spice_level: str | None = Field(None, max_length=20)
    allergies: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class GuestUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=200)
    address: str | None = None
    dietary_preference: str | None = Field(None, max_length=100)
    spice_level: str | None = Field(None, max_length=20)
    allergies: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class GuestResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    phone: str | None
    email: str | None
    address: str | None
    dietary_preference: str | None
    spice_level: str | None
    allergies: str | None
    notes: str | None
    tags: list[str] | None
    total_visits: int
    total_spend: float
    last_visit_at: datetime | None
    loyalty_points: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GuestLoyaltyAdjust(BaseModel):
    points: int = Field(..., description="Positive to add, negative to redeem")
    reason: str = Field(..., max_length=200)
