"""
Sync service – handles bulk ingest of offline POS orders & payments.

POS devices collect orders and payments in local SQLite while offline.
When connectivity resumes, the Flutter app calls /sync/orders and
/sync/payments to push batches to the PostgreSQL central database.

Each record is processed individually so a single bad record does not
block the rest of the batch.
"""

import uuid
from datetime import timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orders import Order, OrderItem, Payment
from app.models.products import Product
from app.schemas.order_schema import (
    SyncOrder,
    SyncPayment,
    SyncResponse,
)


async def sync_orders(db: AsyncSession, orders: list[SyncOrder]) -> SyncResponse:
    """
    Ingest a batch of offline orders.

    Returns counts of successfully synced vs failed records.
    """
    synced = 0
    failed = 0
    errors: list[str] = []

    for payload in orders:
        try:
            order_id = uuid.uuid4()
            gross = Decimal("0")
            tax = Decimal("0")
            items: list[OrderItem] = []

            for item in payload.items:
                result = await db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = result.scalar_one_or_none()
                tax_pct = Decimal(str(product.tax_percent)) if product else Decimal("0")

                item_total = Decimal(str(item.price)) * item.quantity
                item_tax = item_total * tax_pct / Decimal("100")
                gross += item_total
                tax += item_tax

                items.append(
                    OrderItem(
                        id=uuid.uuid4(),
                        order_id=order_id,
                        product_id=item.product_id,
                        product_name=product.name if product else "",
                        quantity=item.quantity,
                        price=float(item.price),
                        tax_amount=float(item_tax),
                        total=float(item_total),
                    )
                )

            discount = Decimal(str(payload.discount_amount))
            net = gross + tax - discount

            order = Order(
                id=order_id,
                store_id=payload.store_id,
                employee_id=payload.employee_id,
                terminal_id=payload.terminal_id,
                table_number=payload.table_number,
                order_type=payload.order_type,
                gross_amount=float(gross),
                tax_amount=float(tax),
                discount_amount=float(discount),
                net_amount=float(net),
                payment_status="pending",
                device_id=payload.device_id,
                sync_status="synced",
                created_at=payload.created_at.replace(tzinfo=timezone.utc)
                if payload.created_at.tzinfo is None
                else payload.created_at,
            )

            db.add(order)
            db.add_all(items)
            await db.flush()
            synced += 1

        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append(f"Order from device {payload.device_id}: {exc}")

    return SyncResponse(synced=synced, failed=failed, errors=errors)


async def sync_payments(db: AsyncSession, payments: list[SyncPayment]) -> SyncResponse:
    """Ingest a batch of offline payments."""
    synced = 0
    failed = 0
    errors: list[str] = []

    for p in payments:
        try:
            payment = Payment(
                id=uuid.uuid4(),
                order_id=p.order_id,
                payment_method=p.payment_method,
                amount=float(p.amount),
                paid_at=p.paid_at.replace(tzinfo=timezone.utc)
                if p.paid_at.tzinfo is None
                else p.paid_at,
                device_id=p.device_id,
                sync_status="synced",
            )
            db.add(payment)
            await db.flush()

            # Mark order as completed if payment covers full amount
            result = await db.execute(
                select(Order).where(Order.id == p.order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                total_paid_result = await db.execute(
                    select(func.coalesce(func.sum(Payment.amount), 0)).where(
                        Payment.order_id == order.id,
                        Payment.is_refund.is_(False),
                    )
                )
                total_paid = float(total_paid_result.scalar())
                if total_paid >= float(order.net_amount):
                    order.payment_status = "completed"
                    if order.status == "completed":
                        order.status = "paid"
                elif total_paid > 0:
                    order.payment_status = "partial"
                else:
                    order.payment_status = "pending"

            synced += 1

        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append(f"Payment for order {p.order_id}: {exc}")

    return SyncResponse(synced=synced, failed=failed, errors=errors)
