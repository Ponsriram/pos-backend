from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Store, POSTerminal
from app.models.users import User
from app.schemas.user_schema import POSTerminalCreate, POSTerminalResponse
from app.utils.auth import get_current_user, create_terminal_token

router = APIRouter(prefix="/terminals", tags=["Terminals"])


@router.post(
    "/register",
    response_model=POSTerminalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a POS terminal device",
)
async def register_terminal(
    payload: POSTerminalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registers a new POS terminal for a given store.
    Returns the terminal details and its long-lived JWT token.
    Only Admins (Owners) can register terminals.
    """
    # Verify store belongs to admin
    store_res = await db.execute(
        select(Store).where(Store.id == payload.store_id, Store.owner_id == current_user.id)
    )
    if not store_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store not found or access denied"
        )

    # Check if terminal already exists
    existing_term = await db.execute(
        select(POSTerminal).where(POSTerminal.device_identifier == payload.device_identifier)
    )
    if existing_term.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A terminal with this device identifier already exists."
        )

    terminal = POSTerminal(
        store_id=payload.store_id,
        device_name=payload.device_name,
        device_identifier=payload.device_identifier,
    )
    db.add(terminal)
    await db.flush()
    await db.refresh(terminal)
    
    jwt_token = create_terminal_token(terminal_id=terminal.id, store_id=payload.store_id)
    
    return {
        "id": terminal.id,
        "store_id": terminal.store_id,
        "device_name": terminal.device_name,
        "device_identifier": terminal.device_identifier,
        "is_active": terminal.is_active,
        "created_at": terminal.created_at,
        "terminal_token": jwt_token
    }


@router.get(
    "",
    summary="List all registered terminals for all stores owned by the admin",
)
async def list_terminals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all terminals across all stores owned by the current admin."""
    # A bit complex because terminal doesn't have owner_id, but store does.
    result = await db.execute(
        select(POSTerminal)
        .join(Store, Store.id == POSTerminal.store_id)
        .where(Store.owner_id == current_user.id)
    )
    terminals = result.scalars().all()
    # Mask tokens for listing
    return [
        {
            "id": t.id,
            "store_id": t.store_id,
            "device_name": t.device_name,
            "device_identifier": t.device_identifier,
            "is_active": t.is_active,
            "created_at": t.created_at
        }
        for t in terminals
    ]


@router.get(
    "/{terminal_id}",
    summary="Get a specific terminal",
)
async def get_terminal(
    terminal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(POSTerminal)
        .join(Store, Store.id == POSTerminal.store_id)
        .where(POSTerminal.id == terminal_id, Store.owner_id == current_user.id)
    )
    terminal = result.scalar_one_or_none()
    if not terminal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Terminal not found")
        
    return {
        "id": terminal.id,
        "store_id": terminal.store_id,
        "device_name": terminal.device_name,
        "device_identifier": terminal.device_identifier,
        "is_active": terminal.is_active,
        "created_at": terminal.created_at
    }
