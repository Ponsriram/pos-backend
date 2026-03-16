"""
Delivery routes – manage delivery details for orders.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.delivery import DeliveryOrderDetails
from app.models.orders import Order
from app.schemas.delivery_schema import (
    DeliveryDetailsCreate,
    DeliveryDetailsUpdate,
    DeliveryStatusUpdate,
    DeliveryDetailsResponse,
)
from app.utils.auth import get_current_employee, EmployeeContext

router = APIRouter(prefix="/stores/{store_id}/deliveries", tags=["Deliveries"])

def validate_store_access(store_id: UUID, ctx: EmployeeContext):
    if store_id != ctx.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Employee token does not match the requested store"
        )


@router.post("", response_model=DeliveryDetailsResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    store_id: UUID,
    payload: DeliveryDetailsCreate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    
    # Must verify the associated order belongs to the store
    order_res = await db.execute(select(Order).where(Order.id == payload.order_id, Order.store_id == store_id))
    if not order_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found for delivery")
        
    import uuid as _uuid
    delivery = DeliveryOrderDetails(id=_uuid.uuid4(), **payload.model_dump())
    db.add(delivery)
    await db.flush()
    return delivery


@router.get("/{delivery_id}", response_model=DeliveryDetailsResponse)
async def get_delivery(
    store_id: UUID,
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    result = await db.execute(
        select(DeliveryOrderDetails)
        .join(Order, Order.id == DeliveryOrderDetails.order_id)
        .where(DeliveryOrderDetails.id == delivery_id, Order.store_id == store_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery details not found")
    return delivery


@router.put("/{delivery_id}", response_model=DeliveryDetailsResponse)
async def update_delivery(
    store_id: UUID,
    delivery_id: UUID,
    payload: DeliveryDetailsUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    result = await db.execute(
        select(DeliveryOrderDetails)
        .join(Order, Order.id == DeliveryOrderDetails.order_id)
        .where(DeliveryOrderDetails.id == delivery_id, Order.store_id == store_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery details not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(delivery, field, value)
    await db.flush()
    return delivery


@router.put("/{delivery_id}/status", response_model=DeliveryDetailsResponse)
async def update_delivery_status(
    store_id: UUID,
    delivery_id: UUID,
    payload: DeliveryStatusUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    result = await db.execute(
        select(DeliveryOrderDetails)
        .join(Order, Order.id == DeliveryOrderDetails.order_id)
        .where(DeliveryOrderDetails.id == delivery_id, Order.store_id == store_id)
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
    store_id: UUID,
    delivery_status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
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
