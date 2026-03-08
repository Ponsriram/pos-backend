"""
Zone management routes – delivery zone CRUD.

GET    /zones              → list zones
POST   /zones              → create a zone
GET    /zones/{zone_id}    → get zone details
PUT    /zones/{zone_id}    → update a zone
DELETE /zones/{zone_id}    → deactivate a zone
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.zones import Zone, ZoneStoreLink
from app.models.users import User
from app.schemas.zone_schema import ZoneCreate, ZoneUpdate, ZoneResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/zones", tags=["Zones"])


def _to_response(zone: Zone) -> ZoneResponse:
    return ZoneResponse(
        id=zone.id,
        owner_id=zone.owner_id,
        name=zone.name,
        state=zone.state,
        city=zone.city,
        sub_order_type=zone.sub_order_type,
        delivery_fee=float(zone.delivery_fee),
        min_order_amount=float(zone.min_order_amount),
        boundary=zone.boundary,
        is_active=zone.is_active,
        store_ids=[link.store_id for link in zone.store_links],
        created_at=zone.created_at,
    )


def _base_query(owner_id: UUID):
    return (
        select(Zone)
        .options(selectinload(Zone.store_links))
        .where(Zone.owner_id == owner_id)
    )


@router.get("", response_model=list[ZoneResponse])
async def list_zones(
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _base_query(current_user.id)
    if is_active is not None:
        q = q.where(Zone.is_active == is_active)
    q = q.order_by(Zone.created_at.desc())
    result = await db.execute(q)
    return [_to_response(z) for z in result.scalars().unique().all()]


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    payload: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    zone = Zone(
        owner_id=current_user.id,
        name=payload.name,
        state=payload.state,
        city=payload.city,
        sub_order_type=payload.sub_order_type,
        delivery_fee=payload.delivery_fee,
        min_order_amount=payload.min_order_amount,
        boundary=payload.boundary,
    )
    db.add(zone)
    await db.flush()

    for sid in payload.store_ids:
        db.add(ZoneStoreLink(zone_id=zone.id, store_id=sid))
    await db.flush()

    result = await db.execute(
        _base_query(current_user.id).where(Zone.id == zone.id)
    )
    return _to_response(result.scalar_one())


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        _base_query(current_user.id).where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return _to_response(zone)


@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: UUID,
    payload: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        _base_query(current_user.id).where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    for field, value in payload.model_dump(exclude_unset=True, exclude={"store_ids"}).items():
        setattr(zone, field, value)

    if payload.store_ids is not None:
        await db.execute(
            sa_delete(ZoneStoreLink).where(ZoneStoreLink.zone_id == zone.id)
        )
        for sid in payload.store_ids:
            db.add(ZoneStoreLink(zone_id=zone.id, store_id=sid))

    await db.flush()

    result = await db.execute(
        _base_query(current_user.id).where(Zone.id == zone.id)
    )
    return _to_response(result.scalar_one())


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.owner_id == current_user.id)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    zone.is_active = False
    await db.flush()
