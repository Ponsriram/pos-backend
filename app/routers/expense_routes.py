from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Expense
from app.models.users import User
from app.schemas.user_schema import ExpenseCreate, ExpenseResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a store expense",
)
async def create_expense(
    payload: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    expense = Expense(
        store_id=payload.store_id,
        title=payload.title,
        amount=float(payload.amount),
        category=payload.category,
    )
    db.add(expense)
    await db.flush()
    return expense


@router.get(
    "",
    response_model=list[ExpenseResponse],
    summary="List expenses for a store",
)
async def list_expenses(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Expense).where(Expense.store_id == store_id).order_by(Expense.created_at.desc())
    )
    return result.scalars().all()
