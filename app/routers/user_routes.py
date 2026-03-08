"""
User routes – profile management and sub-user (cloud access) management.

GET  /users/me          → current user profile
PUT  /users/me          → update current user profile
GET  /users             → list sub-users managed by the owner
POST /users             → invite/create a sub-user
PUT  /users/{user_id}   → update a sub-user
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.schemas.user_schema import UserResponse, UserUpdate, UserRegister
from app.utils.auth import get_current_user
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


# ── Current User Profile ──────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user's profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update the currently authenticated user's profile",
)
async def update_my_profile(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.flush()
    return current_user


# ── Sub-User Management (Cloud Access) ────────────────────────────────────

@router.get(
    "",
    response_model=list[UserResponse],
    summary="List sub-users managed by the authenticated owner",
)
async def list_users(
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns users created/invited by the current owner.
    Owners see all sub-users; non-owners see only themselves.
    """
    if current_user.role != "owner":
        return [current_user]

    q = select(User).where(
        (User.id == current_user.id) | (User.created_by_id == current_user.id)
    )
    if role:
        q = q.where(User.role == role)
    if is_active is not None:
        q = q.where(User.is_active == is_active)
    q = q.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite/create a sub-user under the current owner",
)
async def create_sub_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can create sub-users",
        )

    # Check for duplicate email
    existing = await db.execute(
        select(func.count()).select_from(User).where(User.email == payload.email)
    )
    if existing.scalar_one() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        created_by_id=current_user.id,
    )
    db.add(user)
    await db.flush()
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a sub-user's details",
)
async def update_sub_user(
    user_id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can manage sub-users",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Owners can only manage their own sub-users
    if user.created_by_id != current_user.id and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot manage this user",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    return user
