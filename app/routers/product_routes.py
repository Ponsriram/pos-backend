"""
Product & Category routes.

POST   /products/categories              → create a category
GET    /products/categories              → list categories for a store
DELETE /products/categories/{category_id} → delete a category
POST   /products                          → create a product
GET    /products                          → list products for a store
PUT    /products/{id}                     → update a product
DELETE /products/{id}                     → delete a product
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.products import Category, Product
from app.models.stores import Store
from app.models.users import User
from app.schemas.product_schema import (
    CategoryCreate,
    CategoryResponse,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/products", tags=["Products"])


# ── Categories ────────────────────────────────────────────────────────────

@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product category",
)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    category = Category(store_id=payload.store_id, name=payload.name)
    db.add(category)
    await db.flush()
    return category


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List categories for a store",
)
async def list_categories(
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Category)
        .where(Category.store_id == store_id)
        .order_by(Category.name)
    )
    return result.scalars().all()


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product category",
    responses={
        404: {"description": "Category not found"},
        403: {"description": "Not authorised to delete this category"},
        409: {"description": "Cannot delete category with existing products"},
    },
)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a product category.

    - The category must belong to a store owned by the authenticated user.
    - Deletion is blocked if any products are still linked to the category.
    """
    # Fetch category
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Verify store ownership
    store_result = await db.execute(
        select(Store).where(Store.id == category.store_id, Store.owner_id == current_user.id)
    )
    if not store_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to delete this category",
        )

    # Check for active dependent products
    product_result = await db.execute(
        select(Product.id).where(
            Product.category_id == category_id,
            Product.is_active.is_(True),
        ).limit(1)
    )
    if product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Products are still assigned to this category.",
        )

    await db.delete(category)
    await db.flush()
    return None


# ── Products ──────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = Product(
        store_id=payload.store_id,
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        price=float(payload.price),
        tax_percent=float(payload.tax_percent),
        is_active=payload.is_active,
    )
    db.add(product)
    await db.flush()
    return product


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="List products for a store (optionally filter by category)",
)
async def list_products(
    store_id: UUID = Query(...),
    category_id: UUID | None = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Product).where(Product.store_id == store_id)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if active_only:
        query = query.where(Product.is_active.is_(True))
    query = query.order_by(Product.name)

    result = await db.execute(query)
    return result.scalars().all()


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update an existing product",
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
    responses={
        404: {"description": "Product not found"},
        403: {"description": "Not authorised to delete this product"},
    },
)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete a product from the database.

    The product must belong to a store owned by the authenticated user.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Verify store ownership
    store_result = await db.execute(
        select(Store).where(Store.id == product.store_id, Store.owner_id == current_user.id)
    )
    if not store_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to delete this product",
        )

    await db.delete(product)
    await db.flush()
    return None
