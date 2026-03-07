"""Pydantic schemas for Delivery order details."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DeliveryDetailsCreate(BaseModel):
    order_id: UUID
    customer_name: str = Field(..., max_length=200)
    customer_phone: str = Field(..., max_length=20)
    delivery_address: str = Field(..., max_length=500)
    landmark: str | None = Field(None, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    delivery_type: str = Field("self", examples=["self", "aggregator", "third_party"])
    delivery_employee_id: UUID | None = None
    delivery_charge: float = Field(0.0, ge=0)
    estimated_delivery_time: datetime | None = None
    delivery_notes: str | None = None


class DeliveryDetailsUpdate(BaseModel):
    customer_name: str | None = Field(None, max_length=200)
    customer_phone: str | None = Field(None, max_length=20)
    delivery_address: str | None = Field(None, max_length=500)
    landmark: str | None = Field(None, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    delivery_type: str | None = None
    delivery_employee_id: UUID | None = None
    delivery_charge: float | None = Field(None, ge=0)
    estimated_delivery_time: datetime | None = None
    delivery_notes: str | None = None


class DeliveryStatusUpdate(BaseModel):
    delivery_status: str = Field(..., examples=["assigned", "picked_up", "in_transit", "delivered", "failed"])
    proof_image_url: str | None = None
    signature_url: str | None = None
    actual_delivery_time: datetime | None = None


class DeliveryDetailsResponse(BaseModel):
    id: UUID
    order_id: UUID
    customer_name: str
    customer_phone: str
    delivery_address: str
    landmark: str | None
    latitude: float | None
    longitude: float | None
    delivery_type: str
    delivery_status: str
    delivery_employee_id: UUID | None
    delivery_charge: float
    estimated_delivery_time: datetime | None
    actual_delivery_time: datetime | None
    proof_image_url: str | None
    signature_url: str | None
    delivery_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
