"""
Employee routes.

POST /employees           → add an employee to a store
GET  /employees           → list employees for a store
POST /employees/pin-login → employee PIN authentication
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Employee
from app.models.users import User
from app.schemas.user_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeePinLoginRequest,
    EmployeePinLoginResponse,
)
from app.services.auth_service import authenticate_employee_pin
from app.utils.auth import get_current_user
from app.utils.security import hash_password

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "/pin-login",
    response_model=EmployeePinLoginResponse,
    summary="Employee PIN login",
    responses={
        401: {"description": "Invalid employee code or PIN"},
        403: {"description": "Employee account is inactive"},
    },
)
async def employee_pin_login(
    payload: EmployeePinLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate an employee using their employee code and PIN.

    Returns a JWT token scoped to the employee and store.
    """
    result = await authenticate_employee_pin(
        employee_code=payload.employee_code,
        pin=payload.pin,
        store_id=payload.store_id,
        db=db,
    )
    return EmployeePinLoginResponse(**result)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an employee to a store",
)
async def add_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    employee = Employee(
        store_id=payload.store_id,
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
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
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
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
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
