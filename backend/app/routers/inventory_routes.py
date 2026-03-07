"""
Inventory routes – items, stock, adjustments, recipes, transfers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.inventory import (
    InventoryItem,
    InventoryUnit,
    InventoryLocation,
    StockLevel,
    Recipe,
    StockTransfer,
)
from app.models.users import User
from app.schemas.inventory_schema import (
    InventoryUnitCreate,
    InventoryUnitResponse,
    InventoryLocationCreate,
    InventoryLocationResponse,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    StockLevelResponse,
    StockAdjustmentCreate,
    StockAdjustmentResponse,
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    StockTransferCreate,
    StockTransferStatusUpdate,
    StockTransferResponse,
    StockTransferLineResponse,
)
from app.services.inventory_service import (
    create_inventory_item,
    update_inventory_item,
    adjust_stock,
    get_stock_levels,
    create_recipe,
    update_recipe,
    get_recipe,
    create_stock_transfer,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ── Units ─────────────────────────────────────────────────────────────────

@router.post("/units", response_model=InventoryUnitResponse, status_code=status.HTTP_201_CREATED)
async def api_create_unit(
    payload: InventoryUnitCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    unit = InventoryUnit(id=_uuid.uuid4(), **payload.model_dump())
    db.add(unit)
    await db.flush()
    return unit


@router.get("/units", response_model=list[InventoryUnitResponse])
async def api_list_units(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(InventoryUnit).where(InventoryUnit.store_id == store_id)
    )
    return result.scalars().all()


# ── Locations ─────────────────────────────────────────────────────────────

@router.post("/locations", response_model=InventoryLocationResponse, status_code=status.HTTP_201_CREATED)
async def api_create_location(
    payload: InventoryLocationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    import uuid as _uuid
    loc = InventoryLocation(id=_uuid.uuid4(), **payload.model_dump())
    db.add(loc)
    await db.flush()
    return loc


@router.get("/locations", response_model=list[InventoryLocationResponse])
async def api_list_locations(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(InventoryLocation).where(InventoryLocation.store_id == store_id)
    )
    return result.scalars().all()


# ── Items ─────────────────────────────────────────────────────────────────

@router.post("/items", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def api_create_item(
    payload: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await create_inventory_item(db, payload)


@router.get("/items", response_model=list[InventoryItemResponse])
async def api_list_items(
    store_id: UUID = Query(...),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(InventoryItem).where(InventoryItem.store_id == store_id)
    if active_only:
        q = q.where(InventoryItem.is_active.is_(True))
    q = q.order_by(InventoryItem.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/items/{item_id}", response_model=InventoryItemResponse)
async def api_update_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return await update_inventory_item(db, item, payload)


# ── Stock Levels ──────────────────────────────────────────────────────────

@router.get("/stock", response_model=list[StockLevelResponse])
async def api_stock_levels(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_stock_levels(db, store_id)


# ── Stock Adjustments ────────────────────────────────────────────────────

@router.post("/stock/adjustments", response_model=StockAdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def api_adjust_stock(
    payload: StockAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await adjust_stock(db, payload, adjusted_by=current_user.id)


# ── Recipes ───────────────────────────────────────────────────────────────

@router.post("/recipes", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def api_create_recipe(
    payload: RecipeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    recipe = await create_recipe(db, payload)
    return await get_recipe(db, recipe.id)


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def api_get_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    recipe = await get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.put("/recipes/{recipe_id}", response_model=RecipeResponse)
async def api_update_recipe(
    recipe_id: UUID,
    payload: RecipeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    recipe = await get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    await update_recipe(db, recipe, payload)
    return await get_recipe(db, recipe_id)


# ── Stock Transfers ───────────────────────────────────────────────────────

@router.post("/transfers", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED)
async def api_create_transfer(
    payload: StockTransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transfer = await create_stock_transfer(db, payload, requested_by=current_user.id)
    result = await db.execute(
        select(StockTransfer)
        .options(selectinload(StockTransfer.lines))
        .where(StockTransfer.id == transfer.id)
    )
    return result.scalar_one()


@router.put("/transfers/{transfer_id}/status", response_model=StockTransferResponse)
async def api_update_transfer_status(
    transfer_id: UUID,
    payload: StockTransferStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StockTransfer)
        .options(selectinload(StockTransfer.lines))
        .where(StockTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    transfer.status = payload.status
    if payload.status == "approved":
        transfer.approved_by = current_user.id
    await db.flush()
    return transfer
