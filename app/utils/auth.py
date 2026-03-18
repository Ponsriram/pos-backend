"""
JWT token creation & validation + FastAPI dependency for
extracting the current authenticated user from the Bearer token.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.users import User
from app.models.stores import POSTerminal, EmployeeSession

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@dataclass
class EmployeeContext:
    employee_id: UUID
    store_id: UUID
    role: str

# ── Token helpers ─────────────────────────────────────────────────────────

def create_admin_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    payload = {
        "sub": str(user_id),
        "type": "admin",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_terminal_token(terminal_id: UUID, store_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    payload = {
        "sub": str(terminal_id),
        "store_id": str(store_id),
        "type": "terminal",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_employee_token(employee_id: UUID, store_id: UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    payload = {
        "sub": str(employee_id),
        "store_id": str(store_id),
        "role": role,
        "type": "employee",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependency ────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload.get("type", "admin") != "admin": # Default to admin if old token for BC
        pass 
    
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_terminal(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> POSTerminal:
    payload = decode_access_token(token)
    if payload.get("type") != "terminal":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Terminal token required")
    
    terminal_id = payload.get("sub")
    result = await db.execute(select(POSTerminal).where(POSTerminal.id == UUID(terminal_id)))
    terminal = result.scalar_one_or_none()
    if not terminal or not terminal.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Terminal inactive or invalid")
    
    return terminal


async def get_current_employee(
    token: str = Depends(oauth2_scheme),
) -> EmployeeContext:
    payload = decode_access_token(token)
    if payload.get("type") != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee token required")
    try:
        ctx = EmployeeContext(
            employee_id=UUID(payload["sub"]),
            store_id=UUID(payload["store_id"]),
            role=payload["role"]
        )
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    return ctx


def require_roles(allowed_roles: list[str]):
    def role_dependency(ctx: EmployeeContext = Depends(get_current_employee)):
        if "admin" not in allowed_roles and ctx.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx
    return role_dependency

async def get_current_user_or_employee(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | EmployeeContext:
    payload = decode_access_token(token)
    typ = payload.get("type", "admin")
    if typ == "employee":
        return await get_current_employee(token)
    else:
        return await get_current_user(token, db)
