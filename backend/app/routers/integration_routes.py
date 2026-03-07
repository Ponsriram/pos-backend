"""
Integration routes – aggregator configs, store links, and webhooks.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.integrations import AggregatorConfig, AggregatorStoreLink, AggregatorOrder
from app.models.users import User
from app.schemas.integration_schema import (
    AggregatorConfigCreate,
    AggregatorConfigUpdate,
    AggregatorConfigResponse,
    AggregatorStoreLinkCreate,
    AggregatorStoreLinkUpdate,
    AggregatorStoreLinkResponse,
    AggregatorOrderResponse,
    AggregatorWebhookPayload,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ── Aggregator Configs ────────────────────────────────────────────────────

@router.post("/aggregators", response_model=AggregatorConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_aggregator(
    payload: AggregatorConfigCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    agg = AggregatorConfig(id=_uuid.uuid4(), **payload.model_dump())
    db.add(agg)
    await db.flush()
    return agg


@router.get("/aggregators", response_model=list[AggregatorConfigResponse])
async def list_aggregators(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AggregatorConfig).order_by(AggregatorConfig.name)
    )
    return result.scalars().all()


@router.put("/aggregators/{agg_id}", response_model=AggregatorConfigResponse)
async def update_aggregator(
    agg_id: UUID,
    payload: AggregatorConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(AggregatorConfig).where(AggregatorConfig.id == agg_id))
    agg = result.scalar_one_or_none()
    if not agg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aggregator not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agg, field, value)
    await db.flush()
    return agg


# ── Store Links ───────────────────────────────────────────────────────────

@router.post("/store-links", response_model=AggregatorStoreLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_store_link(
    payload: AggregatorStoreLinkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    link = AggregatorStoreLink(id=_uuid.uuid4(), **payload.model_dump())
    db.add(link)
    await db.flush()
    return link


@router.get("/store-links", response_model=list[AggregatorStoreLinkResponse])
async def list_store_links(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AggregatorStoreLink).where(AggregatorStoreLink.store_id == store_id)
    )
    return result.scalars().all()


@router.put("/store-links/{link_id}", response_model=AggregatorStoreLinkResponse)
async def update_store_link(
    link_id: UUID,
    payload: AggregatorStoreLinkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(AggregatorStoreLink).where(AggregatorStoreLink.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store link not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(link, field, value)
    await db.flush()
    return link


# ── Aggregator Orders ────────────────────────────────────────────────────

@router.get("/orders", response_model=list[AggregatorOrderResponse])
async def list_aggregator_orders(
    store_id: UUID = Query(...),
    aggregator_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(AggregatorOrder).where(AggregatorOrder.store_id == store_id)
    if aggregator_id:
        q = q.where(AggregatorOrder.aggregator_id == aggregator_id)
    q = q.order_by(AggregatorOrder.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


# ── Webhook (aggregators push orders here) ────────────────────────────────

@router.post("/webhook/{aggregator_code}", status_code=status.HTTP_200_OK)
async def aggregator_webhook(
    aggregator_code: str,
    payload: AggregatorWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Generic webhook endpoint for delivery aggregators.
    Looks up the aggregator by code and stores the raw payload
    for async processing.
    """
    result = await db.execute(
        select(AggregatorConfig).where(AggregatorConfig.code == aggregator_code)
    )
    agg = result.scalar_one_or_none()
    if not agg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown aggregator")

    import uuid as _uuid
    order = AggregatorOrder(
        id=_uuid.uuid4(),
        store_id=_uuid.UUID(int=0),  # resolved during processing
        aggregator_id=agg.id,
        external_order_id=payload.external_order_id,
        external_status=payload.event,
        raw_payload=payload.data,
    )
    db.add(order)
    await db.flush()
    return {"status": "received", "id": str(order.id)}
