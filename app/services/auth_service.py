"""
Employee PIN authentication service.

Provides `authenticate_employee_pin()` which verifies an employee's
code + PIN against the database, creates an EmployeeSession,
and returns a signed JWT with employee-specific claims.
"""

from datetime import datetime, timezone
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stores import Employee, EmployeeSession
from app.utils.security import verify_password
from app.utils.auth import create_employee_token


async def authenticate_employee_pin(
    employee_code: str,
    pin: str,
    store_id: UUID,
    terminal_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Authenticate an employee by code + PIN.

    Steps:
      1. Query employee by employee_code and store_id
      2. Verify bcrypt PIN hash
      3. Check active status
      4. Generate EmployeeSession
      5. Generate JWT token
      6. Return token + employee details
    """
    result = await db.execute(
        select(Employee).where(
            Employee.employee_code == employee_code,
            Employee.store_id == store_id,
        )
    )
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee code or PIN",
        )

    if not verify_password(pin, employee.pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee code or PIN",
        )

    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is inactive",
        )

    # Create session
    jti = str(uuid.uuid4())
    session = EmployeeSession(
        employee_id=employee.id,
        terminal_id=terminal_id,
        token_jti=jti,
        is_active=True,
    )
    db.add(session)
    await db.flush()

    access_token = create_employee_token(
        employee_id=employee.id,
        store_id=employee.store_id,
        terminal_id=terminal_id,
        role=employee.role,
        jti=jti
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "employee_id": employee.id,
        "employee_name": employee.name,
        "role": employee.role,
        "store_id": employee.store_id,
    }
