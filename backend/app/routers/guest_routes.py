"""
Guest / CRM routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.guests import Guest
from app.models.users import User
from app.schemas.guest_schema import (
    GuestCreate,
    GuestUpdate,
    GuestResponse,
    GuestLoyaltyAdjust,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/guests", tags=["Guests"])


@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
async def create_guest(
    payload: GuestCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    guest = Guest(id=_uuid.uuid4(), **payload.model_dump())
    db.add(guest)
    await db.flush()
    return guest


@router.get("", response_model=list[GuestResponse])
async def list_guests(
    store_id: UUID = Query(...),
    search: str | None = Query(None, description="Search by name or phone"),
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Guest).where(Guest.store_id == store_id)
    if active_only:
        q = q.where(Guest.is_active.is_(True))
    if search:
        q = q.where(
            Guest.name.ilike(f"%{search}%") | Guest.phone.ilike(f"%{search}%")
        )
    q = q.order_by(Guest.name).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{guest_id}", response_model=GuestResponse)
async def get_guest(
    guest_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Guest).where(Guest.id == guest_id))
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return guest


@router.put("/{guest_id}", response_model=GuestResponse)
async def update_guest(
    guest_id: UUID,
    payload: GuestUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Guest).where(Guest.id == guest_id))
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(guest, field, value)
    await db.flush()
    return guest


@router.post("/{guest_id}/loyalty", response_model=GuestResponse)
async def adjust_loyalty(
    guest_id: UUID,
    payload: GuestLoyaltyAdjust,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Guest).where(Guest.id == guest_id))
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    guest.loyalty_points += payload.points
    if guest.loyalty_points < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient loyalty points")
    await db.flush()
    return guest
