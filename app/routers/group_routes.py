"""
Permission Group routes – admin groups and biller groups.

GET  /groups              → list groups
POST /groups              → create a group
GET  /groups/{group_id}   → get group details
PUT  /groups/{group_id}   → update a group
DELETE /groups/{group_id} → deactivate a group
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.groups import PermissionGroup, PermissionGroupMember, PermissionGroupStore
from app.models.users import User
from app.schemas.group_schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
    PermissionGroupResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/groups", tags=["Permission Groups"])


def _to_response(group: PermissionGroup) -> PermissionGroupResponse:
    return PermissionGroupResponse(
        id=group.id,
        owner_id=group.owner_id,
        name=group.name,
        group_type=group.group_type,
        permissions=group.permissions,
        is_active=group.is_active,
        store_ids=[s.store_id for s in group.stores],
        member_user_ids=[m.user_id for m in group.members],
        created_at=group.created_at,
    )


def _base_query(owner_id: UUID):
    return (
        select(PermissionGroup)
        .options(
            selectinload(PermissionGroup.members),
            selectinload(PermissionGroup.stores),
        )
        .where(PermissionGroup.owner_id == owner_id)
    )


@router.get("", response_model=list[PermissionGroupResponse])
async def list_groups(
    group_type: str | None = Query(None, description="admin or biller"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _base_query(current_user.id)
    if group_type:
        q = q.where(PermissionGroup.group_type == group_type)
    q = q.order_by(PermissionGroup.created_at.desc())
    result = await db.execute(q)
    return [_to_response(g) for g in result.scalars().unique().all()]


@router.post("", response_model=PermissionGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: PermissionGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = PermissionGroup(
        owner_id=current_user.id,
        name=payload.name,
        group_type=payload.group_type,
        permissions=payload.permissions,
    )
    db.add(group)
    await db.flush()

    for sid in payload.store_ids:
        db.add(PermissionGroupStore(group_id=group.id, store_id=sid))
    for uid in payload.member_user_ids:
        db.add(PermissionGroupMember(group_id=group.id, user_id=uid))
    await db.flush()

    # Re-fetch with relationships
    result = await db.execute(
        _base_query(current_user.id).where(PermissionGroup.id == group.id)
    )
    return _to_response(result.scalar_one())


@router.get("/{group_id}", response_model=PermissionGroupResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        _base_query(current_user.id).where(PermissionGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return _to_response(group)


@router.put("/{group_id}", response_model=PermissionGroupResponse)
async def update_group(
    group_id: UUID,
    payload: PermissionGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        _base_query(current_user.id).where(PermissionGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    for field, value in payload.model_dump(exclude_unset=True, exclude={"store_ids", "member_user_ids"}).items():
        setattr(group, field, value)

    if payload.store_ids is not None:
        await db.execute(
            sa_delete(PermissionGroupStore).where(PermissionGroupStore.group_id == group.id)
        )
        for sid in payload.store_ids:
            db.add(PermissionGroupStore(group_id=group.id, store_id=sid))

    if payload.member_user_ids is not None:
        await db.execute(
            sa_delete(PermissionGroupMember).where(PermissionGroupMember.group_id == group.id)
        )
        for uid in payload.member_user_ids:
            db.add(PermissionGroupMember(group_id=group.id, user_id=uid))

    await db.flush()

    result = await db.execute(
        _base_query(current_user.id).where(PermissionGroup.id == group.id)
    )
    return _to_response(result.scalar_one())


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PermissionGroup).where(
            PermissionGroup.id == group_id,
            PermissionGroup.owner_id == current_user.id,
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group.is_active = False
    await db.flush()
