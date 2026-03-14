"""
Extended order service – handles order lifecycle, cancellation,
table transfers, and enhanced order creation with new fields.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orders import Order, OrderItem, Payment
from app.models.products import Product
from app.schemas.order_schema import (
    OrderCreate,
    OrderUpdate,
    OrderCancelRequest,
    OrderTransferRequest,
    OrderAddItemRequest,
    OrderUpdateItemRequest,
    PaymentCreate,
    PaymentUpdate,
    RefundRequest,
)


async def _next_order_number(db: AsyncSession, store_id: uuid.UUID) -> str:
    """Generate a sequential order number per store: ORD-0001, ORD-0002, …"""
    result = await db.execute(
        select(func.count(Order.id)).where(Order.store_id == store_id)
    )
    count = result.scalar() or 0
    return f"ORD-{count + 1:04d}"


async def create_order(db: AsyncSession, payload: OrderCreate) -> Order:
    order_id = uuid.uuid4()
    gross = Decimal("0")
    tax = Decimal("0")
    items: list[OrderItem] = []

    for item in payload.items:
        result = await db.execute(select(Product).where(Product.id == item.product_id))
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
                notes=item.notes,
            )
        )

    discount = Decimal(str(payload.discount_amount))
    service_charge = Decimal(str(payload.service_charge))
    net = gross + tax + service_charge - discount

    order_number = await _next_order_number(db, payload.store_id)

    order = Order(
        id=order_id,
        store_id=payload.store_id,
        employee_id=payload.employee_id,
        terminal_id=payload.terminal_id,
        table_number=payload.table_number,
        guest_id=payload.guest_id,
        shift_id=payload.shift_id,
        order_number=order_number,
        order_type=payload.order_type,
        channel=payload.channel,
        gross_amount=float(gross),
        tax_amount=float(tax),
        discount_amount=float(discount),
        service_charge=float(service_charge),
        net_amount=float(net),
        payment_status="pending",
        status="open",
        notes=payload.notes,
    )

    db.add(order)
    db.add_all(items)
    await db.flush()
    return order


async def update_order_status(
    db: AsyncSession, order: Order, new_status: str
) -> Order:
    """Advance order through a strict lifecycle with order-type-specific fulfillment."""
    allowed_transitions = {
        "open": {"sent_to_kitchen", "cancelled"},
        "sent_to_kitchen": {"preparing", "cancelled"},
        "preparing": {"ready", "cancelled"},
        # Split fulfillment path by order type once food is ready.
        "ready": {
            "served" if order.order_type == "dine_in" else None,
            "handed_over" if order.order_type in ("takeaway", "take_away") else None,
            "out_for_delivery" if order.order_type in ("delivery", "aggregator") else None,
            "cancelled",
        }
        - {None},
        "served": {"completed", "cancelled"},
        "handed_over": {"completed", "cancelled"},
        "out_for_delivery": {"delivered", "cancelled"},
        "delivered": {"completed", "cancelled"},
        "completed": {"paid"},
        "paid": set(),
        "cancelled": set(),
    }
    current = order.status or "open"
    if new_status not in allowed_transitions.get(current, set()):
        raise ValueError(
            f"Cannot transition from '{current}' to '{new_status}'"
        )
    order.status = new_status
    order.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return order


async def cancel_order(
    db: AsyncSession,
    order: Order,
    reason: str,
    cancelled_by: uuid.UUID | None = None,
) -> Order:
    if order.status in ("completed", "paid", "cancelled"):
        raise ValueError(f"Cannot cancel order in '{order.status}' status")

    # If any amount was collected already, create an automatic refund so
    # cancelled+paid orders are financially settled.
    charge_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.order_id == order.id,
            Payment.is_refund.is_(False),
        )
    )
    refund_result = await db.execute(
        select(func.coalesce(func.sum(-Payment.amount), 0)).where(
            Payment.order_id == order.id,
            Payment.is_refund.is_(True),
        )
    )
    net_paid = float(charge_result.scalar()) - float(refund_result.scalar())

    if net_paid > 0:
        db.add(
            Payment(
                id=uuid.uuid4(),
                order_id=order.id,
                payment_method="refund",
                amount=-abs(net_paid),
                is_refund=True,
                reference=f"Auto refund on cancellation: {reason}",
            )
        )

    order.status = "cancelled"
    order.cancel_reason = reason
    order.cancelled_by = cancelled_by
    order.cancelled_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)
    await _recalculate_payment_state(db, order)
    await db.flush()
    return order


async def transfer_order(
    db: AsyncSession, order: Order, payload: OrderTransferRequest
) -> Order:
    if payload.table_number is not None:
        order.table_number = payload.table_number
    if payload.employee_id is not None:
        order.employee_id = payload.employee_id
    order.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return order


def _is_payment_unlock_status(order: Order) -> bool:
    """Return True when an order has reached a pay-eligible stage."""
    status = (order.status or "").lower()
    order_type = (order.order_type or "").lower()

    if status in {"paid", "completed"}:
        return True

    # Dine-in can be settled once it is served.
    if order_type == "dine_in":
        return status in {"served", "ready"}

    # Takeaway can be settled once food is ready/handed over.
    if order_type in {"takeaway", "take_away"}:
        return status in {"ready", "handed_over"}

    # Delivery/aggregator may be settled once dispatched or delivered.
    if order_type in {"delivery", "aggregator"}:
        return status in {"ready", "out_for_delivery", "delivered"}

    return False


def _is_fulfillment_completed(order: Order) -> bool:
    """Operational fulfillment finished, regardless of payment."""
    return (order.status or "").lower() in {
        "completed",
        "served",
        "handed_over",
        "delivered",
    }


async def _recalculate_payment_state(db: AsyncSession, order: Order) -> None:
    """Recompute order payment status from charges and refunds."""
    charge_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.order_id == order.id,
            Payment.is_refund.is_(False),
        )
    )
    refund_result = await db.execute(
        select(func.coalesce(func.sum(-Payment.amount), 0)).where(
            Payment.order_id == order.id,
            Payment.is_refund.is_(True),
        )
    )

    total_charged = float(charge_result.scalar())
    total_refunded = float(refund_result.scalar())
    net_paid = total_charged - total_refunded

    if total_charged <= 0 and total_refunded <= 0:
        order.payment_status = "pending"
        if order.status == "paid":
            order.status = "completed"
            order.updated_at = datetime.now(timezone.utc)
        return

    # Fully refunded payments should be explicitly filterable in sales reports.
    if total_refunded > 0 and net_paid <= 0:
        order.payment_status = "refunded"
        if order.status == "paid":
            order.status = "completed"
            order.updated_at = datetime.now(timezone.utc)
        return

    if net_paid >= float(order.net_amount):
        order.payment_status = "completed"
        # Mark fully settled only when fulfillment is actually finished.
        if order.status == "completed" or (
            order.status == "paid" and _is_fulfillment_completed(order)
        ):
            order.status = "paid"
            order.updated_at = datetime.now(timezone.utc)
    elif net_paid > 0:
        order.payment_status = "partial"
        # If a paid order gets edited below full amount, roll back paid state.
        if order.status == "paid":
            order.status = "completed"
            order.updated_at = datetime.now(timezone.utc)
    else:
        order.payment_status = "pending"
        if order.status == "paid":
            order.status = "completed"
            order.updated_at = datetime.now(timezone.utc)


async def create_payment(db: AsyncSession, payload: PaymentCreate) -> Payment:
    result = await db.execute(select(Order).where(Order.id == payload.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")

    if order.status == "cancelled":
        raise ValueError("Cannot take payment for a cancelled order")

    # Allow prepayment at any active stage; keep paid/finalization coupled to fulfillment.
    # _is_payment_unlock_status is still useful for UI guidance, but not hard-gated here.

    payment = Payment(
        id=uuid.uuid4(),
        order_id=payload.order_id,
        payment_method=payload.payment_method,
        amount=float(payload.amount),
        tip_amount=float(payload.tip_amount),
        reference=payload.reference,
    )
    db.add(payment)

    await db.flush()
    await _recalculate_payment_state(db, order)

    await db.flush()
    return payment


async def update_payment(
    db: AsyncSession,
    payment_id: uuid.UUID,
    payload: PaymentUpdate,
) -> Payment:
    """Edit a recorded payment (for billing mistakes/corrections)."""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise ValueError("Payment not found")
    if payment.is_refund:
        raise ValueError("Refund entries cannot be edited")

    if payload.payment_method is not None:
        payment.payment_method = payload.payment_method
    if payload.amount is not None:
        payment.amount = float(payload.amount)
    if payload.tip_amount is not None:
        payment.tip_amount = float(payload.tip_amount)
    if payload.reference is not None:
        payment.reference = payload.reference

    order_result = await db.execute(select(Order).where(Order.id == payment.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        await db.flush()
        await _recalculate_payment_state(db, order)

    await db.flush()
    return payment


async def create_refund(db: AsyncSession, payload: RefundRequest) -> Payment:
    original_payment_result = await db.execute(
        select(Payment).where(Payment.id == payload.payment_id)
    )
    original_payment = original_payment_result.scalar_one_or_none()
    if not original_payment:
        raise ValueError("Original payment not found")

    refund = Payment(
        id=uuid.uuid4(),
        order_id=original_payment.order_id,
        payment_method="refund",
        amount=-abs(float(payload.amount)),
        is_refund=True,
        original_payment_id=payload.payment_id,
        reference=payload.reason,
    )
    db.add(refund)
    await db.flush()

    order_result = await db.execute(select(Order).where(Order.id == refund.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        await _recalculate_payment_state(db, order)
        await db.flush()

    return refund


# ── Order Item CRUD ───────────────────────────────────────────────────────

def _recalculate_order_totals(order: Order):
    """Recompute order totals from its active items."""
    gross = Decimal("0")
    tax = Decimal("0")
    for item in order.items:
        if item.status == "active":
            gross += Decimal(str(item.total))
            tax += Decimal(str(item.tax_amount))
    discount = Decimal(str(order.discount_amount))
    service_charge = Decimal(str(order.service_charge))
    order.gross_amount = float(gross)
    order.tax_amount = float(tax)
    order.net_amount = float(gross + tax + service_charge - discount)


async def add_order_item(
    db: AsyncSession, order: Order, payload: OrderAddItemRequest
) -> OrderItem:
    """Add a new item to an existing open/in-progress order."""
    if order.status in ("completed", "paid", "cancelled"):
        raise ValueError(f"Cannot add items to order in '{order.status}' status")

    # Look up product for tax
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    tax_pct = Decimal(str(product.tax_percent)) if product else Decimal("0")

    item_total = Decimal(str(payload.price)) * payload.quantity
    item_tax = item_total * tax_pct / Decimal("100")

    item = OrderItem(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=payload.product_id,
        product_name=product.name if product else "",
        quantity=payload.quantity,
        price=float(payload.price),
        tax_amount=float(item_tax),
        total=float(item_total),
        notes=payload.notes,
        kitchen_status="pending",
    )
    db.add(item)
    await db.flush()

    # Refresh items list and recalculate
    await db.refresh(order, attribute_names=["items"])
    _recalculate_order_totals(order)
    order.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return item


async def update_order_item(
    db: AsyncSession, order: Order, item_id: uuid.UUID, payload: OrderUpdateItemRequest
) -> OrderItem:
    """Update quantity or notes of an order item."""
    if order.status in ("completed", "paid", "cancelled"):
        raise ValueError(f"Cannot update items on order in '{order.status}' status")

    item = None
    for oi in order.items:
        if oi.id == item_id:
            item = oi
            break
    if not item:
        raise ValueError("Order item not found")
    if item.status != "active":
        raise ValueError(f"Cannot update item in '{item.status}' status")

    if payload.quantity is not None:
        item.quantity = payload.quantity
        item.total = float(Decimal(str(item.price)) * payload.quantity)
        # Recalculate tax proportionally
        result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = result.scalar_one_or_none()
        tax_pct = Decimal(str(product.tax_percent)) if product else Decimal("0")
        item.tax_amount = float(Decimal(str(item.total)) * tax_pct / Decimal("100"))

    if payload.notes is not None:
        item.notes = payload.notes

    _recalculate_order_totals(order)
    order.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return item


async def delete_order_item(
    db: AsyncSession, order: Order, item_id: uuid.UUID
) -> OrderItem:
    """Soft-delete (cancel) an order item."""
    if order.status in ("completed", "paid", "cancelled"):
        raise ValueError(f"Cannot remove items from order in '{order.status}' status")

    item = None
    for oi in order.items:
        if oi.id == item_id:
            item = oi
            break
    if not item:
        raise ValueError("Order item not found")
    if item.kot_id is not None:
        raise ValueError("Cannot remove item already sent to kitchen; cancel it instead")

    item.status = "cancelled"
    _recalculate_order_totals(order)
    order.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return item
