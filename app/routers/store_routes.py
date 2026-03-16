"""
Store management routes.

All endpoints require JWT authentication. The authenticated user
is automatically treated as the store owner.

POST /stores                  → create a new store
GET  /stores                  → list stores belonging to the current user
GET  /stores/{store_id}       → get a single store
PUT  /stores/{store_id}       → update a store
GET  /stores/{store_id}/tables→ dynamically generated table labels
POST /stores/terminals        → register a POS terminal
POST /stores/expenses         → record an expense
GET  /stores/expenses         → list expenses for a store
"""

from uuid import UUID
from datetime import datetime, timezone as tz

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Store
from app.models.users import User
from app.schemas.user_schema import (
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    StoreTablesResponse,
    TableLabel,
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
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )
    for field, value in update_data.items():
        setattr(store, field, value)
    store.updated_at = datetime.now(tz.utc)
    await db.flush()
    return store


# ── Dynamic table labels ──────────────────────────────────────────────────

@router.get(
    "/{store_id}/tables",
    response_model=StoreTablesResponse,
    summary="Get dynamically generated table labels for a store",
)
async def get_store_tables(
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
    tables = [
        TableLabel(table_number=i, table_label=f"T{i}")
        for i in range(1, store.table_count + 1)
    ]
    return StoreTablesResponse(
        store_id=store.id,
        table_count=store.table_count,
        tables=tables,
    )



