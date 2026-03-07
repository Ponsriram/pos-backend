"""Audit service – write audit log entries."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    store_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
    description: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        store_id=store_id,
        user_id=user_id,
        employee_id=employee_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry
