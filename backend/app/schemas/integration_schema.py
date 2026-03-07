"""Pydantic schemas for Aggregator integrations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Aggregator Config ─────────────────────────────────────────────────────

class AggregatorConfigCreate(BaseModel):
    code: str = Field(..., max_length=50, examples=["swiggy", "zomato", "uber_eats"])
    name: str = Field(..., max_length=100)
    webhook_secret_header: str | None = Field(None, max_length=100)


class AggregatorConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    webhook_secret_header: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class AggregatorConfigResponse(BaseModel):
    id: UUID
    code: str
    name: str
    webhook_secret_header: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Aggregator Store Link ────────────────────────────────────────────────

class AggregatorStoreLinkCreate(BaseModel):
    store_id: UUID
    aggregator_id: UUID
    external_store_id: str = Field(..., max_length=200)
    api_key: str | None = Field(None, max_length=500)
    api_secret: str | None = Field(None, max_length=500)
    config: dict | None = None
    is_enabled: bool = True


class AggregatorStoreLinkUpdate(BaseModel):
    external_store_id: str | None = Field(None, max_length=200)
    api_key: str | None = Field(None, max_length=500)
    api_secret: str | None = Field(None, max_length=500)
    config: dict | None = None
    is_enabled: bool | None = None


class AggregatorStoreLinkResponse(BaseModel):
    id: UUID
    store_id: UUID
    aggregator_id: UUID
    external_store_id: str
    config: dict | None
    is_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Aggregator Order ─────────────────────────────────────────────────────

class AggregatorOrderResponse(BaseModel):
    id: UUID
    store_id: UUID
    aggregator_id: UUID
    external_order_id: str
    internal_order_id: UUID | None
    external_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AggregatorWebhookPayload(BaseModel):
    """Generic payload accepted from aggregator webhooks."""
    event: str = Field(..., examples=["order_placed", "order_cancelled", "status_update"])
    external_order_id: str
    data: dict
