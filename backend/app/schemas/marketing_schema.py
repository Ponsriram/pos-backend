"""Pydantic schemas for Audit Log and Marketing Campaigns."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Audit Log ─────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: UUID
    store_id: UUID | None
    user_id: UUID | None
    employee_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    description: str | None
    old_values: dict | None
    new_values: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Campaign ──────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=200)
    subject: str | None = Field(None, max_length=200)
    content: str | None = None
    target_segment: str | None = Field(None, max_length=100, examples=["all", "vip", "inactive", "new"])
    segment_filters: dict | None = None
    scheduled_at: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    subject: str | None = Field(None, max_length=200)
    content: str | None = None
    target_segment: str | None = Field(None, max_length=100)
    segment_filters: dict | None = None
    scheduled_at: datetime | None = None
    status: str | None = Field(None, examples=["draft", "scheduled", "sending", "sent", "cancelled"])


class CampaignResponse(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    subject: str | None
    content: str | None
    target_segment: str | None
    segment_filters: dict | None
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    total_recipients: int
    total_sent: int
    total_opened: int
    total_clicked: int
    created_at: datetime

    model_config = {"from_attributes": True}
