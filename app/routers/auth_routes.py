"""
Authentication routes – register & login.

POST /auth/register  → create a new user (restaurant owner)
POST /auth/login     → authenticate & return JWT
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.schemas.user_schema import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    EmployeePinLoginRequest,
    EmployeePinLoginResponse,
)
from app.utils.security import hash_password, verify_password
from app.utils.auth import create_admin_token, get_current_user
from app.services.auth_service import authenticate_employee_pin

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Register ──────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new restaurant owner",
    responses={
        409: {"description": "Email already registered"},
    },
)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Creates a new User record.

    - Checks for duplicate email.
    - Hashes the password with bcrypt.
    - Returns the created user (without password_hash).
    """
    # Duplicate check
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    return user


# ── Login ─────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain a JWT access token",
    responses={
        401: {"description": "Invalid email or password"},
    },
)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Validates credentials and returns a signed JWT.

    The token should be included in subsequent requests as:
        Authorization: Bearer <token>
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_admin_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


# ── Refresh Admin Token ───────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an admin JWT token",
)
async def refresh_admin_token(current_user: User = Depends(get_current_user)):
    """Refresh the current admin token."""
    token = create_admin_token(current_user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(current_user))


# ── Employee Login ────────────────────────────────────────────────────────

@router.post(
    "/employee-login",
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
    Authenticate an employee using their employee code and PIN on a registered terminal.
    Requires terminal ID validation (provided in schema).
    """
    result = await authenticate_employee_pin(
        employee_code=payload.employee_code,
        pin=payload.pin,
        db=db,
    )
    return EmployeePinLoginResponse(**result)
