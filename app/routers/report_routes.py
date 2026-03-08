"""
Report routes – report templates and report generation.

GET  /reports/types              → list available report templates
POST /reports/generate           → generate a report run
GET  /reports/{report_id}        → get a report run with results
GET  /reports                    → list report runs for the user
"""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.reports import ReportTemplate, ReportRun
from app.models.orders import Order, OrderItem, Payment
from app.models.stores import Store
from app.models.users import User
from app.utils.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


# ── Schemas ───────────────────────────────────────────────────────────────

class ReportTemplateResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    category: str
    parameters_schema: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportGenerateRequest(BaseModel):
    template_code: str = Field(..., examples=["all_restaurant_sales"])
    store_id: UUID
    parameters: dict | None = Field(None, examples=[{"start_date": "2026-01-01", "end_date": "2026-01-31"}])


class ReportRunResponse(BaseModel):
    id: UUID
    template_id: UUID
    store_id: UUID
    requested_by: UUID
    parameters: dict | None
    status: str
    result: dict | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Seed templates (run once on first call) ───────────────────────────────

PREDEFINED_TEMPLATES = [
    ("all_restaurant_sales", "All Restaurant Sales", "sales", "Aggregated sales across all stores"),
    ("item_wise_sales", "Item Wise Sales", "sales", "Sales broken down by product/item"),
    ("invoice_report", "Invoice Report", "finance", "Invoice listing with payment details"),
    ("pax_sales", "Pax Sales", "sales", "Sales per customer/pax count"),
    ("category_wise_sales", "Category Wise Sales", "sales", "Sales per product category"),
    ("daily_sales", "Daily Sales", "sales", "Day-by-day sales summary"),
    ("hourly_sales", "Hourly Sales", "sales", "Hour-by-hour sales breakdown"),
    ("payment_mode_report", "Payment Mode Report", "finance", "Sales by payment method"),
    ("discount_report", "Discount Report", "finance", "Discount usage and amounts"),
    ("tax_report", "Tax Report", "finance", "Tax collected by tax group"),
    ("employee_performance", "Employee Performance", "staff", "Per-employee sales and order count"),
    ("shift_report", "Shift Report", "operations", "Shift-wise sales and cash summary"),
    ("inventory_valuation", "Inventory Valuation", "inventory", "Current stock value report"),
    ("stock_movement", "Stock Movement", "inventory", "Stock ins/outs over a period"),
    ("purchase_report", "Purchase Report", "inventory", "Purchase order summary"),
    ("wastage_report", "Wastage Report", "inventory", "Stock wastage and loss report"),
    ("customer_report", "Customer Report", "sales", "Guest/customer visit and spend analysis"),
    ("aggregator_sales", "Aggregator Sales", "sales", "Sales from delivery aggregators"),
    ("void_cancel_report", "Void & Cancel Report", "operations", "Cancelled and voided orders"),
    ("expense_report", "Expense Report", "finance", "Store operational expenses"),
    ("tip_report", "Tip Report", "finance", "Tips collected per employee/shift"),
    ("service_charge_report", "Service Charge Report", "finance", "Service charges collected"),
]


async def _ensure_templates(db: AsyncSession) -> None:
    """Insert predefined templates if they don't exist."""
    result = await db.execute(select(func.count()).select_from(ReportTemplate))
    if result.scalar_one() > 0:
        return
    for code, name, category, desc in PREDEFINED_TEMPLATES:
        db.add(ReportTemplate(code=code, name=name, category=category, description=desc))
    await db.flush()


# ── Routes ────────────────────────────────────────────────────────────────

@router.get("/types", response_model=list[ReportTemplateResponse])
async def list_report_types(
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _ensure_templates(db)
    q = select(ReportTemplate).where(ReportTemplate.is_active.is_(True))
    if category:
        q = q.where(ReportTemplate.category == category)
    q = q.order_by(ReportTemplate.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/generate", response_model=ReportRunResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    payload: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_templates(db)

    # Find template
    result = await db.execute(
        select(ReportTemplate).where(ReportTemplate.code == payload.template_code)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report template not found")

    # Verify store ownership
    store_result = await db.execute(
        select(Store).where(Store.id == payload.store_id, Store.owner_id == current_user.id)
    )
    if not store_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    # Generate the report synchronously for now
    report_data = await _run_report(db, template.code, payload.store_id, payload.parameters or {})

    run = ReportRun(
        template_id=template.id,
        store_id=payload.store_id,
        requested_by=current_user.id,
        parameters=payload.parameters,
        status="completed",
        result=report_data,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    return run


@router.get("/{report_id}", response_model=ReportRunResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReportRun).where(
            ReportRun.id == report_id,
            ReportRun.requested_by == current_user.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return run


@router.get("", response_model=list[ReportRunResponse])
async def list_reports(
    store_id: UUID | None = Query(None),
    template_code: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ReportRun).where(ReportRun.requested_by == current_user.id)
    if store_id:
        q = q.where(ReportRun.store_id == store_id)
    if template_code:
        tpl = await db.execute(
            select(ReportTemplate).where(ReportTemplate.code == template_code)
        )
        tpl_obj = tpl.scalar_one_or_none()
        if tpl_obj:
            q = q.where(ReportRun.template_id == tpl_obj.id)
    q = q.order_by(ReportRun.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


# ── Internal report runner ────────────────────────────────────────────────

async def _run_report(db: AsyncSession, code: str, store_id: UUID, params: dict) -> dict:
    """Simple report generation. Returns structured data."""
    start_str = params.get("start_date")
    end_str = params.get("end_date")
    start_dt = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) if start_str else None
    end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc) if end_str else None

    filters = [Order.store_id == store_id, Order.payment_status == "completed"]
    if start_dt:
        filters.append(Order.created_at >= start_dt)
    if end_dt:
        filters.append(Order.created_at <= end_dt)

    if code in ("all_restaurant_sales", "daily_sales"):
        q = select(
            func.date_trunc("day", Order.created_at).label("day"),
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.gross_amount), 0).label("gross_sales"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("tax"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
            func.coalesce(func.sum(Order.net_amount), 0).label("net_sales"),
        ).where(*filters).group_by("day").order_by("day")
        result = await db.execute(q)
        rows = [
            {
                "date": str(r.day.date()) if r.day else None,
                "total_orders": r.total_orders,
                "gross_sales": float(r.gross_sales),
                "tax": float(r.tax),
                "discounts": float(r.discounts),
                "net_sales": float(r.net_sales),
            }
            for r in result.all()
        ]
        return {"rows": rows, "type": code}

    elif code == "payment_mode_report":
        q = (
            select(
                Payment.payment_method,
                func.count(Payment.id).label("count"),
                func.coalesce(func.sum(Payment.amount), 0).label("total"),
            )
            .join(Order, Payment.order_id == Order.id)
            .where(*filters)
            .group_by(Payment.payment_method)
        )
        result = await db.execute(q)
        rows = [
            {"method": r.payment_method, "count": r.count, "total": float(r.total)}
            for r in result.all()
        ]
        return {"rows": rows, "type": code}

    elif code == "item_wise_sales":
        q = (
            select(
                OrderItem.product_id,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.total).label("revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(*filters, OrderItem.status == "active")
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.total).desc())
        )
        result = await db.execute(q)
        rows = [
            {"product_id": str(r.product_id), "quantity_sold": int(r.qty), "revenue": float(r.revenue)}
            for r in result.all()
        ]
        return {"rows": rows, "type": code}

    # Fallback: basic summary for unimplemented report types
    q = select(
        func.count(Order.id).label("total_orders"),
        func.coalesce(func.sum(Order.net_amount), 0).label("net_sales"),
        func.coalesce(func.sum(Order.gross_amount), 0).label("gross_sales"),
        func.coalesce(func.sum(Order.tax_amount), 0).label("tax"),
        func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
    ).where(*filters)
    result = await db.execute(q)
    row = result.one()
    return {
        "type": code,
        "total_orders": row.total_orders,
        "net_sales": float(row.net_sales),
        "gross_sales": float(row.gross_sales),
        "tax": float(row.tax),
        "discounts": float(row.discounts),
    }
