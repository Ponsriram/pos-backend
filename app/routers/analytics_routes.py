"""
Analytics routes – dashboard data endpoints.

All amounts are scoped to a single store and an optional date range.

GET /analytics/summary → full dashboard summary
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orders import Order, Payment
from app.models.stores import Store
from app.models.users import User
from app.schemas.order_schema import AnalyticsSummary
from app.utils.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Dashboard analytics summary for a store",
)
async def get_summary(
    store_id: UUID = Query(...),
    start_date: date | None = Query(None, description="Inclusive start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Inclusive end date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Returns aggregated financial metrics for the dashboard:

    - total_revenue (net_amount of completed orders)
    - total_orders
    - tax_collected
    - gross_sales
    - net_sales
    - total_discounts
    - payment_breakdown (cash / card / upi)
    """

    # ── Base filter ───────────────────────────────────────────────────────
    filters = [
        Order.store_id == store_id,
        Order.payment_status == "completed",
    ]
    if start_date:
        filters.append(
            Order.created_at >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        )
    if end_date:
        # Use next day midnight for inclusive end-of-day
        next_day = end_date + timedelta(days=1)
        filters.append(
            Order.created_at < datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
        )

    # ── Order aggregates ──────────────────────────────────────────────────
    order_q = select(
        func.coalesce(func.sum(Order.net_amount), 0).label("total_revenue"),
        func.count(Order.id).label("total_orders"),
        func.coalesce(func.sum(Order.tax_amount), 0).label("tax_collected"),
        func.coalesce(func.sum(Order.gross_amount), 0).label("gross_sales"),
        func.coalesce(func.sum(Order.net_amount), 0).label("net_sales"),
        func.coalesce(func.sum(Order.discount_amount), 0).label("total_discounts"),
    ).where(*filters)

    result = await db.execute(order_q)
    row = result.one()

    # ── Payment breakdown ─────────────────────────────────────────────────
    pay_q = (
        select(
            Payment.payment_method,
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .join(Order, Payment.order_id == Order.id)
        .where(*filters, Payment.is_refund.is_(False))
        .group_by(Payment.payment_method)
    )

    pay_result = await db.execute(pay_q)
    payment_breakdown = {method: float(amount) for method, amount in pay_result.all()}

    return AnalyticsSummary(
        total_revenue=float(row.total_revenue),
        total_orders=int(row.total_orders),
        tax_collected=float(row.tax_collected),
        gross_sales=float(row.gross_sales),
        net_sales=float(row.net_sales),
        total_discounts=float(row.total_discounts),
        payment_breakdown=payment_breakdown,
    )


# ── Multi-Store Analytics ─────────────────────────────────────────────────

class OutletStat(BaseModel):
    store_id: UUID
    store_name: str
    total_revenue: float
    total_orders: int
    tax_collected: float
    gross_sales: float
    net_sales: float
    total_discounts: float
    payment_breakdown: dict[str, float]


class OutletAnalyticsResponse(BaseModel):
    outlets: list[OutletStat]
    totals: AnalyticsSummary


@router.get(
    "/summary/by-store",
    response_model=OutletAnalyticsResponse,
    summary="Per-store analytics breakdown for all stores owned by the user",
)
async def get_summary_by_store(
    start_date: date | None = Query(None, description="Inclusive start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Inclusive end date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns per-store financial metrics for all stores
    owned by the authenticated user, plus an aggregate total.
    """
    # Fetch all user stores
    stores_result = await db.execute(
        select(Store).where(Store.owner_id == current_user.id)
    )
    stores = stores_result.scalars().all()

    outlets: list[OutletStat] = []
    agg_revenue = agg_orders = agg_tax = agg_gross = agg_net = agg_disc = 0.0
    agg_pay: dict[str, float] = {}

    for store in stores:
        filters = [
            Order.store_id == store.id,
            Order.payment_status == "completed",
        ]
        if start_date:
            filters.append(
                Order.created_at >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
            )
        if end_date:
            next_day = end_date + timedelta(days=1)
            filters.append(
                Order.created_at < datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
            )

        order_q = select(
            func.coalesce(func.sum(Order.net_amount), 0).label("total_revenue"),
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("tax_collected"),
            func.coalesce(func.sum(Order.gross_amount), 0).label("gross_sales"),
            func.coalesce(func.sum(Order.net_amount), 0).label("net_sales"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("total_discounts"),
        ).where(*filters)

        result = await db.execute(order_q)
        row = result.one()

        pay_q = (
            select(
                Payment.payment_method,
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .join(Order, Payment.order_id == Order.id)
            .where(*filters, Payment.is_refund.is_(False))
            .group_by(Payment.payment_method)
        )
        pay_result = await db.execute(pay_q)
        store_payment_breakdown = {method: float(amount) for method, amount in pay_result.all()}

        stat = OutletStat(
            store_id=store.id,
            store_name=store.name,
            total_revenue=float(row.total_revenue),
            total_orders=int(row.total_orders),
            tax_collected=float(row.tax_collected),
            gross_sales=float(row.gross_sales),
            net_sales=float(row.net_sales),
            total_discounts=float(row.total_discounts),
            payment_breakdown=store_payment_breakdown,
        )
        outlets.append(stat)

        agg_revenue += stat.total_revenue
        agg_orders += stat.total_orders
        agg_tax += stat.tax_collected
        agg_gross += stat.gross_sales
        agg_net += stat.net_sales
        agg_disc += stat.total_discounts
        for method, amount in store_payment_breakdown.items():
            agg_pay[method] = agg_pay.get(method, 0.0) + amount

    return OutletAnalyticsResponse(
        outlets=outlets,
        totals=AnalyticsSummary(
            total_revenue=agg_revenue,
            total_orders=int(agg_orders),
            tax_collected=agg_tax,
            gross_sales=agg_gross,
            net_sales=agg_net,
            total_discounts=agg_disc,
            payment_breakdown=agg_pay,
        ),
    )
