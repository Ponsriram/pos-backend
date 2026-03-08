"""
Chain / Franchise management routes.

GET  /chains                → list chains owned by the user
POST /chains                → create a new chain
PUT  /chains/{chain_id}     → update a chain
GET  /chains/{chain_id}     → get chain details
GET  /chains/{chain_id}/stores → list stores in a chain
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Chain, Store
from app.models.users import User
from app.schemas.user_schema import ChainCreate, ChainResponse, StoreResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/chains", tags=["Chains / Franchise"])


class ChainUpdate(ChainCreate):
    name: str | None = None  # type: ignore[assignment]
    logo_url: str | None = None


@router.get(
    "",
    response_model=list[ChainResponse],
    summary="List all chains owned by the authenticated user",
)
async def list_chains(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Chain).where(Chain.owner_id == current_user.id).order_by(Chain.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "",
    response_model=ChainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chain / brand",
)
async def create_chain(
    payload: ChainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chain = Chain(
        owner_id=current_user.id,
        name=payload.name,
        logo_url=payload.logo_url,
    )
    db.add(chain)
    await db.flush()
    return chain


@router.get(
    "/{chain_id}",
    response_model=ChainResponse,
    summary="Get a single chain by ID",
)
async def get_chain(
    chain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Chain).where(Chain.id == chain_id, Chain.owner_id == current_user.id)
    )
    chain = result.scalar_one_or_none()
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain not found")
    return chain


@router.put(
    "/{chain_id}",
    response_model=ChainResponse,
    summary="Update a chain",
)
async def update_chain(
    chain_id: UUID,
    payload: ChainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Chain).where(Chain.id == chain_id, Chain.owner_id == current_user.id)
    )
    chain = result.scalar_one_or_none()
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(chain, field, value)
    await db.flush()
    return chain


@router.get(
    "/{chain_id}/stores",
    response_model=list[StoreResponse],
    summary="List all stores belonging to a chain",
)
async def list_chain_stores(
    chain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify chain ownership
    chain_result = await db.execute(
        select(Chain).where(Chain.id == chain_id, Chain.owner_id == current_user.id)
    )
    if not chain_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain not found")

    result = await db.execute(
        select(Store).where(Store.chain_id == chain_id).order_by(Store.created_at.desc())
    )
    return result.scalars().all()
