"""
Marketing / Campaign routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.marketing import Campaign
from app.models.users import User
from app.schemas.marketing_schema import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/marketing", tags=["Marketing"])


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    campaign = Campaign(id=_uuid.uuid4(), **payload.model_dump())
    db.add(campaign)
    await db.flush()
    return campaign


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    store_id: UUID = Query(...),
    campaign_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Campaign).where(Campaign.store_id == store_id)
    if campaign_status:
        q = q.where(Campaign.status == campaign_status)
    q = q.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    await db.flush()
    return campaign
