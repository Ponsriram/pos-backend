"""
Pydantic schemas for User / Auth / Store / Employee / Table / Expense endpoints.

Separates request bodies (Create) from response bodies (Response)
to avoid leaking sensitive fields like password_hash.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Registration / Login ──────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, examples=["Tejas Prasad"])
    email: EmailStr = Field(..., examples=["tejas@example.com"])
    phone: str | None = Field(None, max_length=20, examples=["+919876543210"])
    password: str = Field(..., min_length=8, examples=["Str0ngP@ss!"])
    role: str = Field("owner", examples=["owner"])


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["tejas@example.com"])
    password: str = Field(..., examples=["Str0ngP@ss!"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse | None" = None


# ── User Response ─────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None


# ── User Permission ──────────────────────────────────────────────────────

class PermissionCreate(BaseModel):
    permission: str = Field(..., max_length=100, examples=["orders.cancel"])
    store_id: UUID | None = None


class PermissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    permission: str
    store_id: UUID | None

    model_config = {"from_attributes": True}


# ── Chain ─────────────────────────────────────────────────────────────────

class ChainCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Spice Route Restaurants"])
    logo_url: str | None = Field(None, max_length=500)


class ChainResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    logo_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Store ─────────────────────────────────────────────────────────────────

class StoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Downtown Bistro"])
    location: str | None = Field(None, examples=["123 MG Road, Bangalore"])
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)
    timezone: str = Field("Asia/Kolkata", max_length=64)
    currency: str = Field("INR", max_length=3)
    tax_inclusive: bool = False
    chain_id: UUID | None = None


class StoreUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    currency: str | None = None
    tax_inclusive: bool | None = None
    chain_id: UUID | None = None
    is_active: bool | None = None


class StoreResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    location: str | None
    phone: str | None
    email: str | None
    timezone: str
    currency: str
    tax_inclusive: bool
    chain_id: UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── POS Terminal ──────────────────────────────────────────────────────────

class POSTerminalCreate(BaseModel):
    store_id: UUID
    device_name: str = Field(..., max_length=120, examples=["Counter-1 iPad"])
    device_identifier: str = Field(..., max_length=255, examples=["IPAD-A1B2C3"])


class POSTerminalResponse(BaseModel):
    id: UUID
    store_id: UUID
    device_name: str
    device_identifier: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Employee ──────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    store_id: UUID
    name: str = Field(..., max_length=120, examples=["Ravi Kumar"])
    employee_code: str = Field(..., max_length=20, examples=["EMP001"])
    pin: str = Field(..., max_length=10, examples=["1234"])
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)
    role: str = Field("cashier", max_length=50, examples=["cashier"])
    user_id: UUID | None = None
    permissions: list[str] | None = None


class EmployeeUpdate(BaseModel):
    name: str | None = None
    pin: str | None = None
    phone: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None
    permissions: list[str] | None = None


class EmployeeResponse(BaseModel):
    id: UUID
    store_id: UUID
    user_id: UUID | None
    name: str
    employee_code: str
    phone: str | None
    email: str | None
    role: str
    is_active: bool
    permissions: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dine-In Table ────────────────────────────────────────────────────────

class DineInTableCreate(BaseModel):
    store_id: UUID
    table_number: int = Field(..., ge=1, examples=[1])
    label: str | None = Field(None, max_length=50)
    capacity: int = Field(4, ge=1, examples=[4])
    status: str = Field("available", examples=["available"])
    section: str | None = Field(None, max_length=50, examples=["Main Hall"])
    zone: str | None = Field(None, max_length=50)
    position_x: int | None = None
    position_y: int | None = None


class DineInTableUpdate(BaseModel):
    table_number: int | None = None
    label: str | None = None
    capacity: int | None = None
    status: str | None = None
    section: str | None = None
    zone: str | None = None
    position_x: int | None = None
    position_y: int | None = None
    is_active: bool | None = None


class DineInTableResponse(BaseModel):
    id: UUID
    store_id: UUID
    table_number: int
    label: str | None
    capacity: int
    status: str
    section: str | None
    zone: str | None
    position_x: int | None
    position_y: int | None
    is_active: bool
    current_order_id: UUID | None

    model_config = {"from_attributes": True}


class TableMergeRequest(BaseModel):
    """Merge multiple tables into one order."""
    table_ids: list[UUID] = Field(..., min_length=2)
    order_id: UUID


class OrderSplitRequest(BaseModel):
    """Split an order's items into multiple new orders on different tables."""
    splits: list["SplitGroup"] = Field(..., min_length=2)


class SplitGroup(BaseModel):
    table_id: UUID
    item_ids: list[UUID] = Field(..., min_length=1)


# ── Expense ───────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    store_id: UUID
    title: str = Field(..., max_length=200, examples=["Vegetable purchase"])
    amount: float = Field(..., gt=0, examples=[1500.00])
    category: str | None = Field(None, max_length=100, examples=["ingredients"])
    notes: str | None = None
    shift_id: UUID | None = None


class ExpenseResponse(BaseModel):
    id: UUID
    store_id: UUID
    title: str
    amount: float
    category: str | None
    notes: str | None
    shift_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pagination ────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Generic paginated wrapper."""
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 1
