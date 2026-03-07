"""
Delivery routes – manage delivery details for orders.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.delivery import DeliveryOrderDetails
from app.models.users import User
from app.schemas.delivery_schema import (
    DeliveryDetailsCreate,
    DeliveryDetailsUpdate,
    DeliveryStatusUpdate,
    DeliveryDetailsResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


@router.post("", response_model=DeliveryDetailsResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    payload: DeliveryDetailsCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    delivery = DeliveryOrderDetails(id=_uuid.uuid4(), **payload.model_dump())
    db.add(delivery)
    await db.flush()
    return delivery


@router.get("/{order_id}", response_model=DeliveryDetailsResponse)
async def get_delivery(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrderDetails).where(DeliveryOrderDetails.order_id == order_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery details not found")
    return delivery


@router.put("/{order_id}", response_model=DeliveryDetailsResponse)
async def update_delivery(
    order_id: UUID,
    payload: DeliveryDetailsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrderDetails).where(DeliveryOrderDetails.order_id == order_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery details not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(delivery, field, value)
    await db.flush()
    return delivery


@router.put("/{order_id}/status", response_model=DeliveryDetailsResponse)
async def update_delivery_status(
    order_id: UUID,
    payload: DeliveryStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrderDetails).where(DeliveryOrderDetails.order_id == order_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery details not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(delivery, field, value)
    await db.flush()
    return delivery


@router.get("", response_model=list[DeliveryDetailsResponse])
async def list_deliveries(
    store_id: UUID = Query(..., description="Not directly on delivery; join via order"),
    delivery_status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.models.orders import Order
    q = (
        select(DeliveryOrderDetails)
        .join(Order, Order.id == DeliveryOrderDetails.order_id)
        .where(Order.store_id == store_id)
    )
    if delivery_status:
        q = q.where(DeliveryOrderDetails.delivery_status == delivery_status)
    q = q.order_by(DeliveryOrderDetails.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()
