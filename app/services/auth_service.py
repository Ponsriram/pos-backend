"""
Employee PIN authentication service.

Provides `authenticate_employee_pin()` which verifies an employee's
code + PIN against the database and returns a signed JWT with
employee-specific claims.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.stores import Employee
from app.utils.security import verify_password

settings = get_settings()

EMPLOYEE_TOKEN_EXPIRE_HOURS = 8


def _create_employee_token(employee_id: UUID, store_id: UUID) -> str:
    """Create a JWT containing employee-specific claims."""
    expire = datetime.now(timezone.utc) + timedelta(hours=EMPLOYEE_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(employee_id),
        "employee_id": str(employee_id),
        "store_id": str(store_id),
        "type": "employee",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def authenticate_employee_pin(
    employee_code: str,
    pin: str,
    store_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Authenticate an employee by code + PIN.

    Steps:
      1. Query employee by employee_code and store_id
      2. Verify bcrypt PIN hash
      3. Check active status
      4. Generate JWT token
      5. Return token + employee details

    Raises:
        HTTPException 401 – employee not found or invalid PIN
        HTTPException 403 – employee account is inactive
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

    access_token = _create_employee_token(employee.id, employee.store_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "employee_id": employee.id,
        "employee_name": employee.name,
        "store_id": employee.store_id,
    }
