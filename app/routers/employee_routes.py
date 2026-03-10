"""
Employee routes.

POST /employees           → add an employee to a store
GET  /employees           → list employees for a store
POST /employees/pin-login → employee PIN authentication
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Employee
from app.models.users import User
from app.schemas.user_schema import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeePinLoginRequest,
    EmployeePinLoginResponse,
)
from app.services.auth_service import authenticate_employee_pin
from app.utils.auth import get_current_user

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
        pin=payload.pin,
        role=payload.role,
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
