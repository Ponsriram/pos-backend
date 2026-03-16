"""
Kitchen display routes – list active KOTs and update their status.

GET  /kitchen/orders              → list active KOTs for a store
PUT  /kitchen/kot/{kot_id}/status → advance KOT status
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.billing import KOT
from app.models.users import User
from app.schemas.billing_schema import KOTResponse, KOTStatusUpdate
from app.services.billing_service import update_kot_status, get_kot
from app.utils.auth import get_current_user_or_employee, EmployeeContext

router = APIRouter(tags=["Kitchen"])


# ── List active kitchen orders ────────────────────────────────────────────

@router.get(
    "/kitchen/orders",
    response_model=list[KOTResponse],
    summary="List active KOTs for kitchen display",
)
async def list_kitchen_orders(
    store_id: UUID = Query(...),
    kot_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User | EmployeeContext = Depends(get_current_user_or_employee),
):
    query = (
        select(KOT)
        .options(selectinload(KOT.items))
        .where(KOT.store_id == store_id)
    )
    if kot_status:
        query = query.where(KOT.status == kot_status)
    else:
        # By default show all active kitchen tickets
        query = query.where(KOT.status.in_(["pending", "preparing", "ready", "served"]))

    query = query.order_by(KOT.created_at.asc())

    result = await db.execute(query)
    return result.scalars().unique().all()


# ── Update KOT status ────────────────────────────────────────────────────

@router.put(
    "/kitchen/kot/{kot_id}/status",
    response_model=KOTResponse,
    summary="Advance a KOT through its lifecycle (pending → preparing → ready → served)",
)
async def api_update_kot_status(
    kot_id: UUID,
    payload: KOTStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User | EmployeeContext = Depends(get_current_user_or_employee),
):
    try:
        kot = await update_kot_status(db, kot_id, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_kot(db, kot.id)
