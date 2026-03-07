"""Ledger service – tax groups, city ledger accounts/transactions."""

import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ledger import TaxGroup, TaxRule, CityLedgerAccount, CityLedgerTransaction
from app.schemas.ledger_schema import (
    TaxGroupCreate,
    TaxGroupUpdate,
    CityLedgerAccountCreate,
    CityLedgerAccountUpdate,
    CityLedgerTransactionCreate,
)


# ── Tax Groups ────────────────────────────────────────────────────────────

async def create_tax_group(db: AsyncSession, payload: TaxGroupCreate) -> TaxGroup:
    group_id = uuid.uuid4()
    rules = [
        TaxRule(id=uuid.uuid4(), group_id=group_id, **r.model_dump())
        for r in payload.rules
    ]
    group = TaxGroup(
        id=group_id,
        **payload.model_dump(exclude={"rules"}),
    )
    db.add(group)
    db.add_all(rules)
    await db.flush()
    return group


async def update_tax_group(db: AsyncSession, group: TaxGroup, payload: TaxGroupUpdate) -> TaxGroup:
    data = payload.model_dump(exclude_unset=True, exclude={"rules"})
    for field, value in data.items():
        setattr(group, field, value)

    if payload.rules is not None:
        await db.execute(delete(TaxRule).where(TaxRule.group_id == group.id))
        new_rules = [
            TaxRule(id=uuid.uuid4(), group_id=group.id, **r.model_dump())
            for r in payload.rules
        ]
        db.add_all(new_rules)

    await db.flush()
    return group


async def get_tax_group(db: AsyncSession, group_id: uuid.UUID) -> TaxGroup | None:
    result = await db.execute(
        select(TaxGroup).options(selectinload(TaxGroup.rules)).where(TaxGroup.id == group_id)
    )
    return result.scalar_one_or_none()


# ── City Ledger Accounts ─────────────────────────────────────────────────

async def create_ledger_account(db: AsyncSession, payload: CityLedgerAccountCreate) -> CityLedgerAccount:
    account = CityLedgerAccount(id=uuid.uuid4(), **payload.model_dump())
    db.add(account)
    await db.flush()
    return account


async def update_ledger_account(
    db: AsyncSession, account: CityLedgerAccount, payload: CityLedgerAccountUpdate
) -> CityLedgerAccount:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await db.flush()
    return account


# ── City Ledger Transactions ─────────────────────────────────────────────

async def create_ledger_transaction(
    db: AsyncSession, payload: CityLedgerTransactionCreate, created_by: uuid.UUID | None = None
) -> CityLedgerTransaction:
    txn = CityLedgerTransaction(
        id=uuid.uuid4(),
        created_by=created_by,
        **payload.model_dump(),
    )
    db.add(txn)

    # Update account balance
    result = await db.execute(
        select(CityLedgerAccount).where(CityLedgerAccount.id == payload.account_id)
    )
    account = result.scalar_one_or_none()
    if account:
        if payload.transaction_type == "charge":
            account.current_balance += payload.amount
        elif payload.transaction_type == "settlement":
            account.current_balance -= payload.amount

    await db.flush()
    return txn
