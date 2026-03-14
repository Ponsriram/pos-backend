"""
Billing routes – KOTs, invoices, bill templates.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.billing import KOT, Invoice, BillTemplate
from app.models.users import User
from app.schemas.billing_schema import (
    KOTCreate,
    KOTStatusUpdate,
    KOTResponse,
    InvoiceGenerateRequest,
    InvoiceResponse,
    BillTemplateCreate,
    BillTemplateUpdate,
    BillTemplateResponse,
)
from app.services.billing_service import create_kot, get_kot, generate_invoice, update_kot_status
from app.utils.auth import get_current_user

router = APIRouter(prefix="/billing", tags=["Billing"])


# ── KOTs ──────────────────────────────────────────────────────────────────

@router.post("/kots", response_model=KOTResponse, status_code=status.HTTP_201_CREATED)
async def api_create_kot(
    payload: KOTCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        kot = await create_kot(
            db, payload.order_id, payload.store_id, payload.item_ids, payload.kitchen_section
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_kot(db, kot.id)


@router.get("/kots/{kot_id}", response_model=KOTResponse)
async def api_get_kot(
    kot_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    kot = await get_kot(db, kot_id)
    if not kot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOT not found")
    return kot


@router.get("/kots", response_model=list[KOTResponse])
async def api_list_kots(
    store_id: UUID = Query(...),
    order_id: UUID | None = Query(None),
    kot_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(KOT).options(selectinload(KOT.items)).where(KOT.store_id == store_id)
    if order_id:
        q = q.where(KOT.order_id == order_id)
    if kot_status:
        q = q.where(KOT.status == kot_status)
    q = q.order_by(KOT.created_at.desc())
    result = await db.execute(q)
    return result.scalars().unique().all()


@router.put("/kots/{kot_id}/status", response_model=KOTResponse)
async def api_update_kot_status(
    kot_id: UUID,
    payload: KOTStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        kot = await update_kot_status(db, kot_id, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_kot(db, kot_id)


# ── Invoices ──────────────────────────────────────────────────────────────

@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def api_generate_invoice(
    payload: InvoiceGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await generate_invoice(db, payload.order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def api_get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.get("/invoices", response_model=list[InvoiceResponse])
async def api_list_invoices(
    store_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.store_id == store_id)
        .order_by(Invoice.issued_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# ── Bill Templates ────────────────────────────────────────────────────────

@router.post("/templates", response_model=BillTemplateResponse, status_code=status.HTTP_201_CREATED)
async def api_create_template(
    payload: BillTemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    tpl = BillTemplate(id=_uuid.uuid4(), **payload.model_dump())
    db.add(tpl)
    await db.flush()
    return tpl


@router.get("/templates", response_model=list[BillTemplateResponse])
async def api_list_templates(
    store_id: UUID = Query(...),
    template_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(BillTemplate).where(BillTemplate.store_id == store_id)
    if template_type:
        q = q.where(BillTemplate.template_type == template_type)
    q = q.order_by(BillTemplate.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/templates/{template_id}", response_model=BillTemplateResponse)
async def api_update_template(
    template_id: UUID,
    payload: BillTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(BillTemplate).where(BillTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, field, value)
    await db.flush()
    return tpl
