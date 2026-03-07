"""Inventory service – stock levels, adjustments, recipes, transfers."""

import uuid
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import (
    InventoryItem,
    InventoryUnit,
    InventoryLocation,
    StockLevel,
    StockAdjustment,
    Recipe,
    RecipeLine,
    StockTransfer,
    StockTransferLine,
)
from app.schemas.inventory_schema import (
    InventoryItemCreate,
    InventoryItemUpdate,
    StockAdjustmentCreate,
    RecipeCreate,
    RecipeUpdate,
    StockTransferCreate,
)


# ── Items ─────────────────────────────────────────────────────────────────

async def create_inventory_item(db: AsyncSession, payload: InventoryItemCreate) -> InventoryItem:
    item = InventoryItem(id=uuid.uuid4(), **payload.model_dump())
    db.add(item)
    await db.flush()
    return item


async def update_inventory_item(
    db: AsyncSession, item: InventoryItem, payload: InventoryItemUpdate
) -> InventoryItem:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    return item


# ── Stock Adjustments ────────────────────────────────────────────────────

async def adjust_stock(
    db: AsyncSession, payload: StockAdjustmentCreate, adjusted_by: uuid.UUID | None = None
) -> StockAdjustment:
    """Create a stock adjustment and update the stock level atomically."""
    adj = StockAdjustment(
        id=uuid.uuid4(),
        adjusted_by=adjusted_by,
        **payload.model_dump(),
    )
    db.add(adj)

    # Upsert stock level
    result = await db.execute(
        select(StockLevel).where(
            StockLevel.item_id == payload.item_id,
            StockLevel.location_id == payload.location_id,
        )
    )
    level = result.scalar_one_or_none()
    if level:
        level.quantity += payload.quantity_change
    else:
        level = StockLevel(
            id=uuid.uuid4(),
            item_id=payload.item_id,
            location_id=payload.location_id,
            quantity=payload.quantity_change,
        )
        db.add(level)

    await db.flush()
    return adj


async def get_stock_levels(db: AsyncSession, store_id: uuid.UUID):
    result = await db.execute(
        select(StockLevel)
        .join(InventoryItem, StockLevel.item_id == InventoryItem.id)
        .where(InventoryItem.store_id == store_id)
    )
    return result.scalars().all()


# ── Recipes ───────────────────────────────────────────────────────────────

async def create_recipe(db: AsyncSession, payload: RecipeCreate) -> Recipe:
    recipe_id = uuid.uuid4()
    lines = [
        RecipeLine(id=uuid.uuid4(), recipe_id=recipe_id, **line.model_dump())
        for line in payload.lines
    ]
    recipe = Recipe(
        id=recipe_id,
        **payload.model_dump(exclude={"lines"}),
    )
    db.add(recipe)
    db.add_all(lines)
    await db.flush()
    return recipe


async def update_recipe(db: AsyncSession, recipe: Recipe, payload: RecipeUpdate) -> Recipe:
    data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    for field, value in data.items():
        setattr(recipe, field, value)

    if payload.lines is not None:
        await db.execute(delete(RecipeLine).where(RecipeLine.recipe_id == recipe.id))
        new_lines = [
            RecipeLine(id=uuid.uuid4(), recipe_id=recipe.id, **line.model_dump())
            for line in payload.lines
        ]
        db.add_all(new_lines)

    await db.flush()
    return recipe


async def get_recipe(db: AsyncSession, recipe_id: uuid.UUID) -> Recipe | None:
    result = await db.execute(
        select(Recipe).options(selectinload(Recipe.lines)).where(Recipe.id == recipe_id)
    )
    return result.scalar_one_or_none()


async def deduct_recipe_stock(
    db: AsyncSession, recipe_id: uuid.UUID, location_id: uuid.UUID, qty: int = 1
):
    """Deduct inventory for `qty` servings of a recipe."""
    recipe = await get_recipe(db, recipe_id)
    if not recipe:
        raise ValueError("Recipe not found")
    for line in recipe.lines:
        needed = Decimal(str(line.quantity)) * qty
        result = await db.execute(
            select(StockLevel).where(
                StockLevel.item_id == line.ingredient_id,
                StockLevel.location_id == location_id,
            )
        )
        level = result.scalar_one_or_none()
        if level:
            level.quantity -= float(needed)


# ── Stock Transfers ───────────────────────────────────────────────────────

async def create_stock_transfer(
    db: AsyncSession, payload: StockTransferCreate, requested_by: uuid.UUID | None = None
) -> StockTransfer:
    transfer_id = uuid.uuid4()
    lines = [
        StockTransferLine(id=uuid.uuid4(), transfer_id=transfer_id, **l.model_dump())
        for l in payload.lines
    ]
    transfer = StockTransfer(
        id=transfer_id,
        from_store_id=payload.from_store_id,
        to_store_id=payload.to_store_id,
        notes=payload.notes,
        requested_by=requested_by,
        status="requested",
    )
    db.add(transfer)
    db.add_all(lines)
    await db.flush()
    return transfer
