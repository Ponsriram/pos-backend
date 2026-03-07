"""
Shift routes – open/close shifts, day close.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.shifts import Shift, DayClose
from app.models.users import User
from app.schemas.shift_schema import (
    ShiftOpen,
    ShiftClose,
    ShiftResponse,
    DayCloseCreate,
    DayCloseResponse,
)
from app.services.shift_service import (
    open_shift,
    close_shift,
    get_shift,
    generate_day_close,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/shifts", tags=["Shifts"])


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def api_open_shift(
    payload: ShiftOpen,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    shift = await open_shift(db, payload)
    return await get_shift(db, shift.id)


@router.get("/{shift_id}", response_model=ShiftResponse)
async def api_get_shift(
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    shift = await get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return shift


@router.get("", response_model=list[ShiftResponse])
async def api_list_shifts(
    store_id: UUID = Query(...),
    shift_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(Shift)
        .options(selectinload(Shift.payment_summaries))
        .where(Shift.store_id == store_id)
    )
    if shift_status:
        q = q.where(Shift.status == shift_status)
    q = q.order_by(Shift.started_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().unique().all()


@router.put("/{shift_id}/close", response_model=ShiftResponse)
async def api_close_shift(
    shift_id: UUID,
    payload: ShiftClose,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    shift = await get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    try:
        shift = await close_shift(db, shift, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_shift(db, shift.id)


# ── Day Close ─────────────────────────────────────────────────────────────

@router.post("/day-close", response_model=DayCloseResponse, status_code=status.HTTP_201_CREATED)
async def api_generate_day_close(
    payload: DayCloseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await generate_day_close(db, payload.store_id, payload.business_date, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/day-close", response_model=list[DayCloseResponse])
async def api_list_day_closes(
    store_id: UUID = Query(...),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(DayClose).where(DayClose.store_id == store_id)
    if start_date:
        q = q.where(DayClose.business_date >= start_date)
    if end_date:
        q = q.where(DayClose.business_date <= end_date)
    q = q.order_by(DayClose.business_date.desc())
    result = await db.execute(q)
    return result.scalars().all()
