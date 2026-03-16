"""Pydantic schemas for User / Auth / Store / Employee / Expense endpoints.

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
    state: str | None = Field(None, max_length=100, examples=["Karnataka"])
    city: str | None = Field(None, max_length=100, examples=["Bangalore"])
    outlet_type: str | None = Field(None, max_length=20, examples=["COFO", "FOFO", "COCO", "FOCO"])
    table_count: int = Field(0, ge=0, examples=[10])


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
    state: str | None = None
    city: str | None = None
    outlet_type: str | None = None
    table_count: int | None = Field(None, ge=0)


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
    state: str | None
    city: str | None
    outlet_type: str | None
    table_count: int
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
    terminal_token: str | None = None

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


class EmployeePinLoginRequest(BaseModel):
    employee_code: str = Field(..., examples=["EMP001"])
    pin: str = Field(..., examples=["1234"])
    store_id: UUID
    terminal_id: UUID


class EmployeePinLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: UUID
    employee_name: str
    store_id: UUID


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


# ── Dynamic Table Labels (generated from table_count) ─────────────────

class TableLabel(BaseModel):
    table_number: int
    table_label: str


class StoreTablesResponse(BaseModel):
    store_id: UUID
    table_count: int
    tables: list[TableLabel]


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
