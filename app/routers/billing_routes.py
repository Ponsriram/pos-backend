"""
Billing routes – KOTs, invoices, bill templates.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.billing import Invoice, BillTemplate
from app.models.users import User
from app.schemas.billing_schema import (
    InvoiceGenerateRequest,
    InvoiceResponse,
    BillTemplateCreate,
    BillTemplateUpdate,
    BillTemplateResponse,
)
from app.services.billing_service import generate_invoice
from app.utils.auth import get_current_employee, EmployeeContext

router = APIRouter(prefix="/stores/{store_id}/billing", tags=["Billing"])

def validate_store_access(store_id: UUID, ctx: EmployeeContext):
    if store_id != ctx.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Employee token does not match the requested store"
        )


# ── Invoices ──────────────────────────────────────────────────────────────

@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def api_generate_invoice(
    store_id: UUID,
    payload: InvoiceGenerateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    try:
        return await generate_invoice(db, payload.order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def api_get_invoice(
    store_id: UUID,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.get("/invoices", response_model=list[InvoiceResponse])
async def api_list_invoices(
    store_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
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
    store_id: UUID,
    payload: BillTemplateCreate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    import uuid as _uuid
    tpl = BillTemplate(id=_uuid.uuid4(), **payload.model_dump())
    db.add(tpl)
    await db.flush()
    return tpl


@router.get("/templates", response_model=list[BillTemplateResponse])
async def api_list_templates(
    store_id: UUID,
    template_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    q = select(BillTemplate).where(BillTemplate.store_id == store_id)
    if template_type:
        q = q.where(BillTemplate.template_type == template_type)
    q = q.order_by(BillTemplate.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/templates/{template_id}", response_model=BillTemplateResponse)
async def api_update_template(
    store_id: UUID,
    template_id: UUID,
    payload: BillTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    validate_store_access(store_id, ctx)
    result = await db.execute(select(BillTemplate).where(BillTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, field, value)
    await db.flush()
    return tpl
