"""
Store management routes.

All endpoints require JWT authentication. The authenticated user
is automatically treated as the store owner.

POST /stores       → create a new store
GET  /stores       → list stores belonging to the current user
POST /stores/terminals  → register a POS terminal
POST /stores/tables     → create a dine-in table
POST /stores/expenses   → record an expense
GET  /stores/expenses   → list expenses for a store
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Store, POSTerminal, DineInTable, Expense
from app.models.users import User
from app.schemas.user_schema import (
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    POSTerminalCreate,
    POSTerminalResponse,
    DineInTableCreate,
    DineInTableResponse,
    ExpenseCreate,
    ExpenseResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/stores", tags=["Stores"])


# ── Create store ──────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new store for the authenticated owner",
)
async def create_store(
    payload: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = Store(
        owner_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(store)
    await db.flush()
    return store


# ── List stores ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[StoreResponse],
    summary="List all stores owned by the authenticated user",
)
async def list_stores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.owner_id == current_user.id).order_by(Store.created_at.desc())
    )
    return result.scalars().all()


# ── Get single store ──────────────────────────────────────────────────────

@router.get(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Get a single store by ID",
)
async def get_store(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.owner_id == current_user.id)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


# ── Update store ──────────────────────────────────────────────────────────

@router.put(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Update a store's details",
)
async def update_store(
    store_id: UUID,
    payload: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.owner_id == current_user.id)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    await db.flush()
    return store


# ── POS Terminal ──────────────────────────────────────────────────────────

@router.post(
    "/terminals",
    response_model=POSTerminalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a POS terminal device",
)
async def create_terminal(
    payload: POSTerminalCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    terminal = POSTerminal(
        store_id=payload.store_id,
        device_name=payload.device_name,
        device_identifier=payload.device_identifier,
    )
    db.add(terminal)
    await db.flush()
    return terminal


# ── Dine-In Table ────────────────────────────────────────────────────────

@router.post(
    "/tables",
    response_model=DineInTableResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a dine-in table to a store",
)
async def create_table(
    payload: DineInTableCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    table = DineInTable(
        store_id=payload.store_id,
        table_number=payload.table_number,
        capacity=payload.capacity,
        status=payload.status,
    )
    db.add(table)
    await db.flush()
    return table


# ── Expenses ──────────────────────────────────────────────────────────────

@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a store expense",
)
async def create_expense(
    payload: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    expense = Expense(
        store_id=payload.store_id,
        title=payload.title,
        amount=float(payload.amount),
        category=payload.category,
    )
    db.add(expense)
    await db.flush()
    return expense


@router.get(
    "/expenses",
    response_model=list[ExpenseResponse],
    summary="List expenses for a store",
)
async def list_expenses(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Expense).where(Expense.store_id == store_id).order_by(Expense.created_at.desc())
    )
    return result.scalars().all()
