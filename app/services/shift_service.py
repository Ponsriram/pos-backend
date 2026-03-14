"""Shift service – open/close shifts and generate day-close reports."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shifts import Shift, ShiftPaymentSummary, DayClose
from app.models.orders import Order, Payment
from app.models.stores import Expense
from app.schemas.shift_schema import ShiftOpen, ShiftClose


async def open_shift(db: AsyncSession, payload: ShiftOpen) -> Shift:
    shift = Shift(
        id=uuid.uuid4(),
        store_id=payload.store_id,
        terminal_id=payload.terminal_id,
        employee_id=payload.employee_id,
        opening_cash=payload.opening_cash,
        notes=payload.notes,
        status="open",
        started_at=datetime.now(timezone.utc),
    )
    db.add(shift)
    await db.flush()
    return shift


async def close_shift(db: AsyncSession, shift: Shift, payload: ShiftClose) -> Shift:
    if shift.status != "open":
        raise ValueError("Shift is not open")

    # Aggregate sales for the shift period
    order_q = select(
        func.coalesce(func.sum(Order.net_amount), 0),
        func.count(Order.id),
    ).where(
        Order.shift_id == shift.id,
        Order.status != "cancelled",
    )
    result = await db.execute(order_q)
    total_sales, total_orders = result.one()

    # Aggregate only cash payments for expected_cash calculation
    cash_q = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Order, Payment.order_id == Order.id)
        .where(
            Order.shift_id == shift.id,
            Order.status != "cancelled",
            Payment.payment_method == "cash",
            Payment.is_refund.is_(False),
        )
    )
    cash_result = await db.execute(cash_q)
    total_cash_sales = cash_result.scalar()

    closing_cash = Decimal(str(payload.closing_cash))
    shift.closing_cash = closing_cash
    shift.total_sales = Decimal(str(total_sales))
    shift.total_orders = int(total_orders)
    shift.expected_cash = shift.opening_cash + Decimal(str(total_cash_sales))
    shift.cash_variance = closing_cash - shift.expected_cash
    shift.notes = payload.notes or shift.notes
    shift.status = "closed"
    shift.ended_at = datetime.now(timezone.utc)

    # Persist payment summaries
    if payload.payment_summaries:
        summaries = [
            ShiftPaymentSummary(
                id=uuid.uuid4(),
                shift_id=shift.id,
                payment_method=ps.payment_method,
                expected_amount=ps.expected_amount,
                actual_amount=ps.actual_amount,
                variance=ps.actual_amount - ps.expected_amount,
            )
            for ps in payload.payment_summaries
        ]
        db.add_all(summaries)

    await db.flush()
    return shift


async def get_shift(db: AsyncSession, shift_id: uuid.UUID) -> Shift | None:
    result = await db.execute(
        select(Shift)
        .options(selectinload(Shift.payment_summaries))
        .where(Shift.id == shift_id)
    )
    return result.scalar_one_or_none()


# ── Day Close ─────────────────────────────────────────────────────────────

async def generate_day_close(
    db: AsyncSession,
    store_id: uuid.UUID,
    business_date: date,
    closed_by: uuid.UUID | None = None,
) -> DayClose:
    """Aggregate all orders/payments/expenses for a business date and persist a DayClose."""
    start = datetime(business_date.year, business_date.month, business_date.day, tzinfo=timezone.utc)
    end = datetime(business_date.year, business_date.month, business_date.day, 23, 59, 59, tzinfo=timezone.utc)

    filters = [
        Order.store_id == store_id,
        Order.created_at >= start,
        Order.created_at <= end,
    ]

    order_q = select(
        func.count(Order.id).label("total_orders"),
        func.coalesce(func.sum(Order.gross_amount), 0).label("gross_sales"),
        func.coalesce(func.sum(Order.tax_amount), 0).label("total_tax"),
        func.coalesce(func.sum(Order.discount_amount), 0).label("total_discounts"),
        func.coalesce(func.sum(Order.service_charge), 0).label("total_service_charge"),
        func.coalesce(func.sum(Order.tip_amount), 0).label("total_tips"),
        func.coalesce(func.sum(Order.net_amount), 0).label("net_sales"),
        func.coalesce(
            func.sum(case((Order.status == "cancelled", 1), else_=0)), 0
        ).label("cancelled_orders"),
    ).where(*filters)

    result = await db.execute(order_q)
    row = result.one()

    # Expenses
    expense_q = select(
        func.coalesce(func.sum(Expense.amount), 0)
    ).where(Expense.store_id == store_id, Expense.created_at >= start, Expense.created_at <= end)
    total_expenses = float((await db.execute(expense_q)).scalar())

    # Payment breakdown
    pay_q = (
        select(Payment.payment_method, func.sum(Payment.amount))
        .join(Order, Payment.order_id == Order.id)
        .where(*filters, Payment.is_refund.is_(False))
        .group_by(Payment.payment_method)
    )
    pay_rows = (await db.execute(pay_q)).all()
    payment_breakdown = {m: float(a) for m, a in pay_rows}

    # Order type breakdown
    otype_q = (
        select(Order.order_type, func.count(Order.id), func.sum(Order.net_amount))
        .where(*filters, Order.status != "cancelled")
        .group_by(Order.order_type)
    )
    otype_rows = (await db.execute(otype_q)).all()
    order_type_breakdown = {t: {"count": c, "amount": float(a)} for t, c, a in otype_rows}

    net_cash = payment_breakdown.get("cash", 0.0) - total_expenses

    day_close = DayClose(
        id=uuid.uuid4(),
        store_id=store_id,
        business_date=business_date,
        total_orders=int(row.total_orders),
        gross_sales=float(row.gross_sales),
        total_tax=float(row.total_tax),
        total_discounts=float(row.total_discounts),
        total_service_charge=float(row.total_service_charge),
        total_tips=float(row.total_tips),
        net_sales=float(row.net_sales),
        total_expenses=total_expenses,
        net_cash=net_cash,
        payment_breakdown=payment_breakdown,
        order_type_breakdown=order_type_breakdown,
        cancelled_orders=int(row.cancelled_orders),
        closed_by=closed_by,
    )
    db.add(day_close)
    await db.flush()
    return day_close
