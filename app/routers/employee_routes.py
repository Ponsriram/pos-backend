"""
Employee routes.

Managed by Admin (owner).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Employee, Store
from app.models.users import User
from app.schemas.user_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
)
from app.utils.auth import get_current_user
from app.utils.security import hash_password

router = APIRouter(prefix="/employees", tags=["Employees"])

async def verify_store_ownership(store_id: UUID, current_user: User, db: AsyncSession):
    store_result = await db.execute(
        select(Store).where(Store.id == store_id, Store.owner_id == current_user.id)
    )
    if not store_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store not found or access denied")

@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an employee to a store",
)
async def add_employee(
    store_id: UUID,
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await verify_store_ownership(store_id, current_user, db)
    
    employee = Employee(
        store_id=store_id,
        name=payload.name,
        employee_code=payload.employee_code,
        pin=hash_password(payload.pin),
        phone=payload.phone,
        email=payload.email,
        role=payload.role,
        permissions={"items": payload.permissions} if payload.permissions else None,
    )
    db.add(employee)
    await db.flush()
    return employee


@router.get(
    "",
    response_model=list[EmployeeResponse],
    summary="List employees for a given store",
)
async def list_employees(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await verify_store_ownership(store_id, current_user, db)
    
    result = await db.execute(
        select(Employee)
        .where(Employee.store_id == store_id)
        .order_by(Employee.created_at.desc())
    )
    return result.scalars().all()


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee details or active status",
)
async def update_employee(
    store_id: UUID,
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await verify_store_ownership(store_id, current_user, db)
    
    result = await db.execute(select(Employee).where(Employee.id == employee_id, Employee.store_id == store_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    data = payload.model_dump(exclude_unset=True)
    permissions = data.pop("permissions", None)
    for field, value in data.items():
        setattr(employee, field, value)

    if permissions is not None:
        employee.permissions = {"items": permissions}

    await db.flush()
    return employee
