"""
Menu routes – menus, items, schedules, pricing rules.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.menus import Menu, MenuItem, MenuPricingRule
from app.models.users import User
from app.schemas.menu_schema import (
    MenuCreate,
    MenuUpdate,
    MenuResponse,
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemResponse,
    MenuScheduleCreate,
    MenuScheduleResponse,
    MenuPricingRuleCreate,
    MenuPricingRuleUpdate,
    MenuPricingRuleResponse,
)
from app.services.menu_service import (
    create_menu,
    update_menu,
    get_menu,
    list_menus,
    create_menu_item,
    update_menu_item,
    set_menu_schedules,
    create_pricing_rule,
    update_pricing_rule,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/menus", tags=["Menus"])


@router.post("", response_model=MenuResponse, status_code=status.HTTP_201_CREATED)
async def api_create_menu(
    payload: MenuCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    menu = await create_menu(db, payload)
    return await get_menu(db, menu.id)


@router.get("", response_model=list[MenuResponse])
async def api_list_menus(
    store_id: UUID = Query(...),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_menus(db, store_id, active_only)


@router.get("/{menu_id}", response_model=MenuResponse)
async def api_get_menu(
    menu_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    menu = await get_menu(db, menu_id)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return menu


@router.put("/{menu_id}", response_model=MenuResponse)
async def api_update_menu(
    menu_id: UUID,
    payload: MenuUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    menu = await get_menu(db, menu_id)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    await update_menu(db, menu, payload)
    return await get_menu(db, menu_id)


# ── Items ─────────────────────────────────────────────────────────────────

@router.post("/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def api_create_menu_item(
    payload: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await create_menu_item(db, payload)


@router.put("/items/{item_id}", response_model=MenuItemResponse)
async def api_update_menu_item(
    item_id: UUID,
    payload: MenuItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return await update_menu_item(db, item, payload)


# ── Schedules ─────────────────────────────────────────────────────────────

@router.put("/{menu_id}/schedules", response_model=list[MenuScheduleResponse])
async def api_set_schedules(
    menu_id: UUID,
    schedules: list[MenuScheduleCreate],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await set_menu_schedules(db, menu_id, schedules)


# ── Pricing Rules ─────────────────────────────────────────────────────────

@router.post("/pricing-rules", response_model=MenuPricingRuleResponse, status_code=status.HTTP_201_CREATED)
async def api_create_pricing_rule(
    payload: MenuPricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await create_pricing_rule(db, payload)


@router.put("/pricing-rules/{rule_id}", response_model=MenuPricingRuleResponse)
async def api_update_pricing_rule(
    rule_id: UUID,
    payload: MenuPricingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(MenuPricingRule).where(MenuPricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing rule not found")
    return await update_pricing_rule(db, rule, payload)
