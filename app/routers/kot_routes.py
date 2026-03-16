"""
Kitchen Order Tickets (KOT) routes.
Unified endpoints for Kitchen and Billing KOT operations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.billing import KOT
from app.schemas.billing_schema import (
    KOTCreate,
    KOTStatusUpdate,
    KOTResponse,
)
from app.services.billing_service import create_kot, get_kot, update_kot_status
from app.utils.auth import get_current_employee, EmployeeContext

router = APIRouter(prefix="/stores/{store_id}/kots", tags=["Kitchen Order Tickets (KOT)"])

def validate_store_access(store_id: UUID, ctx: EmployeeContext):
    if store_id != ctx.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Employee token does not match the requested store"
        )


@router.post("", response_model=KOTResponse, status_code=status.HTTP_201_CREATED)
async def api_create_kot(
    store_id: UUID,
    payload: KOTCreate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    payload.store_id = store_id
    try:
        kot = await create_kot(
            db, payload.order_id, payload.store_id, payload.item_ids, payload.kitchen_section
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_kot(db, kot.id)


@router.get("/{kot_id}", response_model=KOTResponse)
async def api_get_kot(
    store_id: UUID,
    kot_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    kot = await get_kot(db, kot_id)
    if not kot or kot.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOT not found")
    return kot


@router.get("", response_model=list[KOTResponse], summary="List KOTs for a store")
async def api_list_kots(
    store_id: UUID,
    order_id: UUID | None = Query(None),
    kot_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    q = select(KOT).options(selectinload(KOT.items)).where(KOT.store_id == store_id)
    if order_id:
        q = q.where(KOT.order_id == order_id)
    if kot_status:
        q = q.where(KOT.status == kot_status)
    q = q.order_by(KOT.created_at.desc())
    result = await db.execute(q)
    return result.scalars().unique().all()


@router.put("/{kot_id}/status", response_model=KOTResponse)
async def api_update_kot_status(
    store_id: UUID,
    kot_id: UUID,
    payload: KOTStatusUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    kot = await get_kot(db, kot_id)
    if not kot or kot.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOT not found")
    try:
        updated_kot = await update_kot_status(db, kot_id, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_kot(db, kot_id)
