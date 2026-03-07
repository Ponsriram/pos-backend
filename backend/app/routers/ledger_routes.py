"""
Ledger routes – tax groups, city ledger accounts, transactions.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.ledger import TaxGroup, CityLedgerAccount, CityLedgerTransaction
from app.models.users import User
from app.schemas.ledger_schema import (
    TaxGroupCreate,
    TaxGroupUpdate,
    TaxGroupResponse,
    CityLedgerAccountCreate,
    CityLedgerAccountUpdate,
    CityLedgerAccountResponse,
    CityLedgerTransactionCreate,
    CityLedgerTransactionResponse,
)
from app.services.ledger_service import (
    create_tax_group,
    update_tax_group,
    get_tax_group,
    create_ledger_account,
    update_ledger_account,
    create_ledger_transaction,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/ledger", tags=["Ledger"])


# ── Tax Groups ────────────────────────────────────────────────────────────

@router.post("/tax-groups", response_model=TaxGroupResponse, status_code=status.HTTP_201_CREATED)
async def api_create_tax_group(
    payload: TaxGroupCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = await create_tax_group(db, payload)
    return await get_tax_group(db, group.id)


@router.get("/tax-groups", response_model=list[TaxGroupResponse])
async def api_list_tax_groups(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TaxGroup)
        .options(selectinload(TaxGroup.rules))
        .where(TaxGroup.store_id == store_id)
        .order_by(TaxGroup.name)
    )
    return result.scalars().unique().all()


@router.put("/tax-groups/{group_id}", response_model=TaxGroupResponse)
async def api_update_tax_group(
    group_id: UUID,
    payload: TaxGroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = await get_tax_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax group not found")
    await update_tax_group(db, group, payload)
    return await get_tax_group(db, group_id)


# ── City Ledger Accounts ─────────────────────────────────────────────────

@router.post("/accounts", response_model=CityLedgerAccountResponse, status_code=status.HTTP_201_CREATED)
async def api_create_account(
    payload: CityLedgerAccountCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await create_ledger_account(db, payload)


@router.get("/accounts", response_model=list[CityLedgerAccountResponse])
async def api_list_accounts(
    store_id: UUID = Query(...),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(CityLedgerAccount).where(CityLedgerAccount.store_id == store_id)
    if active_only:
        q = q.where(CityLedgerAccount.is_active.is_(True))
    q = q.order_by(CityLedgerAccount.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/accounts/{account_id}", response_model=CityLedgerAccountResponse)
async def api_update_account(
    account_id: UUID,
    payload: CityLedgerAccountUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CityLedgerAccount).where(CityLedgerAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return await update_ledger_account(db, account, payload)


# ── Transactions ──────────────────────────────────────────────────────────

@router.post("/transactions", response_model=CityLedgerTransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_create_transaction(
    payload: CityLedgerTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_ledger_transaction(db, payload, created_by=current_user.id)


@router.get("/transactions", response_model=list[CityLedgerTransactionResponse])
async def api_list_transactions(
    account_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CityLedgerTransaction)
        .where(CityLedgerTransaction.account_id == account_id)
        .order_by(CityLedgerTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
