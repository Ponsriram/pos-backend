"""Menu service – CRUD for menus, items, schedules, and pricing rules."""

import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menus import Menu, MenuItem, MenuSchedule, MenuPricingRule
from app.schemas.menu_schema import (
    MenuCreate,
    MenuUpdate,
    MenuItemCreate,
    MenuItemUpdate,
    MenuPricingRuleCreate,
    MenuPricingRuleUpdate,
    MenuScheduleCreate,
)


async def create_menu(db: AsyncSession, payload: MenuCreate) -> Menu:
    menu = Menu(
        id=uuid.uuid4(),
        **payload.model_dump(),
    )
    db.add(menu)
    await db.flush()
    return menu


async def update_menu(db: AsyncSession, menu: Menu, payload: MenuUpdate) -> Menu:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(menu, field, value)
    await db.flush()
    return menu


async def get_menu(db: AsyncSession, menu_id: uuid.UUID) -> Menu | None:
    result = await db.execute(
        select(Menu)
        .options(selectinload(Menu.items), selectinload(Menu.schedules))
        .where(Menu.id == menu_id)
    )
    return result.scalar_one_or_none()


async def list_menus(db: AsyncSession, store_id: uuid.UUID, active_only: bool = True):
    q = select(Menu).where(Menu.store_id == store_id)
    if active_only:
        q = q.where(Menu.is_active.is_(True))
    q = q.order_by(Menu.sort_order)
    result = await db.execute(q)
    return result.scalars().all()


# ── Menu Items ────────────────────────────────────────────────────────────

async def create_menu_item(db: AsyncSession, payload: MenuItemCreate) -> MenuItem:
    item = MenuItem(id=uuid.uuid4(), **payload.model_dump())
    db.add(item)
    await db.flush()
    return item


async def update_menu_item(db: AsyncSession, item: MenuItem, payload: MenuItemUpdate) -> MenuItem:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    return item


# ── Schedules ─────────────────────────────────────────────────────────────

async def set_menu_schedules(
    db: AsyncSession, menu_id: uuid.UUID, schedules: list[MenuScheduleCreate]
) -> list[MenuSchedule]:
    await db.execute(delete(MenuSchedule).where(MenuSchedule.menu_id == menu_id))
    objs = [MenuSchedule(id=uuid.uuid4(), menu_id=menu_id, **s.model_dump(exclude={"menu_id"})) for s in schedules]
    db.add_all(objs)
    await db.flush()
    return objs


# ── Pricing Rules ─────────────────────────────────────────────────────────

async def create_pricing_rule(db: AsyncSession, payload: MenuPricingRuleCreate) -> MenuPricingRule:
    rule = MenuPricingRule(id=uuid.uuid4(), **payload.model_dump())
    db.add(rule)
    await db.flush()
    return rule


async def update_pricing_rule(
    db: AsyncSession, rule: MenuPricingRule, payload: MenuPricingRuleUpdate
) -> MenuPricingRule:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    return rule
