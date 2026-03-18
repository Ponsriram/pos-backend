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
from app.utils.auth import get_current_employee, EmployeeContext, require_roles

router = APIRouter(prefix="/stores/billing", tags=["Billing"])

def get_target_store(store_id: UUID | None, actor: User | EmployeeContext) -> UUID:
    if isinstance(actor, EmployeeContext):
        if store_id and store_id != actor.store_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store access denied")
        return actor.store_id
    if not store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="store_id required for admin")
    return store_id

# ── Invoices ──────────────────────────────────────────────────────────────

@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def api_generate_invoice(
    payload: InvoiceGenerateRequest,
    store_id: UUID | None = Query(None, description="Inferred from JWT for employees"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    store_id = get_target_store(store_id, ctx)
    try:
        return await generate_invoice(db, payload.order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def api_get_invoice(
    invoice_id: UUID,
    store_id: UUID | None = Query(None, description="Inferred from JWT for employees"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    store_id = get_target_store(store_id, ctx)
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.get("/invoices", response_model=list[InvoiceResponse])
async def api_list_invoices(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    store_id: UUID | None = Query(None, description="Inferred from JWT for employees"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    store_id = get_target_store(store_id, ctx)
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
    store_id: UUID | None = Query(None, description="Inferred from JWT for employees"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    store_id = get_target_store(store_id, ctx)
    import uuid as _uuid
    tpl = BillTemplate(id=_uuid.uuid4(), **payload.model_dump())
    db.add(tpl)
    await db.flush()
    return tpl


@router.get("/templates", response_model=list[BillTemplateResponse])
async def api_list_templates(
    template_type: str | None = Query(None),
    store_id: UUID | None = Query(None, description="Inferred from JWT for employees"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    store_id = get_target_store(store_id, ctx)
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
    store_id: UUID | None = Query(None, description="Inferred from JWT for employees"),
    db: AsyncSession = Depends(get_db),
    ctx: EmployeeContext = Depends(get_current_employee),
):
    store_id = get_target_store(store_id, ctx)
    result = await db.execute(select(BillTemplate).where(BillTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, field, value)
    await db.flush()
    return tpl
