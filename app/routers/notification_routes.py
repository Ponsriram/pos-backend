"""
Notification routes – in-app notifications and device registration.

GET  /notifications                     → list notifications for current user
PUT  /notifications/{id}/read           → mark a notification as read
POST /notifications/mark-all-read       → mark all as read
POST /notifications/devices             → register a device token
GET  /notifications/devices             → list registered devices
DELETE /notifications/devices/{id}      → remove a device token
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notifications import Notification, DeviceToken
from app.models.users import User
from app.schemas.notification_schema import (
    NotificationResponse,
    NotificationMarkRead,
    DeviceTokenCreate,
    DeviceTokenResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── Notifications ─────────────────────────────────────────────────────────

@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    store_id: UUID | None = Query(None),
    category: str | None = Query(None),
    is_read: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Notification).where(Notification.user_id == current_user.id)
    if store_id:
        q = q.where(Notification.store_id == store_id)
    if category:
        q = q.where(Notification.category == category)
    if is_read is not None:
        q = q.where(Notification.is_read == is_read)
    q = q.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    payload: NotificationMarkRead,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = payload.is_read
    await db.flush()
    return notification


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_read(
    store_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        sa_update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
    )
    if store_id:
        q = q.where(Notification.store_id == store_id)
    q = q.values(is_read=True)
    await db.execute(q)
    await db.flush()
    return {"status": "ok"}


# ── Device Tokens ─────────────────────────────────────────────────────────

@router.post(
    "/devices",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    payload: DeviceTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Upsert: if token already exists, update it
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token == payload.token)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.user_id = current_user.id
        existing.platform = payload.platform
        existing.device_name = payload.device_name
        existing.is_active = True
        await db.flush()
        return existing

    device = DeviceToken(
        user_id=current_user.id,
        platform=payload.platform,
        token=payload.token,
        device_name=payload.device_name,
    )
    db.add(device)
    await db.flush()
    return device


@router.get("/devices", response_model=list[DeviceTokenResponse])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.user_id == current_user.id,
            DeviceToken.is_active.is_(True),
        )
    )
    return result.scalars().all()


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.id == device_id,
            DeviceToken.user_id == current_user.id,
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    device.is_active = False
    await db.flush()
