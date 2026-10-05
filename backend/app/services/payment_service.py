"""
Mock Payment Service.

Supports: SUCCESS, FAILED, TIMEOUT outcomes.
Fully idempotent via idempotency_key.
On SUCCESS: confirms inventory, creates order + shipment + notification, single commit.
On FAILED: releases inventory, creates notification.
On TIMEOUT: marks UNKNOWN, reconciliation worker handles.
"""
import uuid
import random
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.inventory_allocator import confirm_inventory, release_inventory
from app.core.event_bus import publish_event, STREAM_PAYMENTS, STREAM_ORDERS
from app.core.metrics import (
    payment_success_total, payment_failure_total, payment_timeout_total,
    duplicate_requests_total, orders_created_total,
)
from app.models.models import Payment, Reservation, Order, OrderItem, Product, Sale, Coupon, Shipment, Notification
from app.core.logging import get_logger

logger = get_logger(__name__)

CARRIERS = ["BlueDart", "Delhivery", "FedEx", "DTDC", "Ekart"]


async def process_payment(
    db: Session,
    reservation_id: str,
    customer_id: str,
    amount: float,
    payment_method: str,
    idempotency_key: str,
    simulate_outcome: str | None = None,
    coupon_code: str | None = None,
    shipping_address: dict | None = None,
) -> tuple[bool, str, "Payment | None", "Order | None"]:
    # Idempotency
    existing_payment = db.query(Payment).filter(
        Payment.idempotency_key == idempotency_key
    ).first()
    if existing_payment:
        duplicate_requests_total.labels(type="payment").inc()
        order = None
        if existing_payment.order_id:
            order = db.query(Order).filter(Order.order_id == existing_payment.order_id).first()
        return existing_payment.status == "SUCCESS", "existing_payment", existing_payment, order

    # Validate reservation
    reservation = db.query(Reservation).filter(
        Reservation.reservation_id == reservation_id
    ).first()
    if not reservation:
        return False, "reservation_not_found", None, None
    if reservation.customer_id != customer_id:
        return False, "unauthorized", None, None
    if reservation.status not in ("RESERVED", "PAYMENT_PENDING"):
        return False, f"invalid_reservation_status:{reservation.status}", None, None
    if reservation.expires_at < datetime.utcnow():
        return False, "reservation_expired", None, None

    outcome = _determine_outcome(simulate_outcome)
    order = None

    if outcome == "SUCCESS":
        reservation.status = "PAYMENT_PENDING"
        reservation.updated_at = datetime.utcnow()
        db.flush()

        confirmed = confirm_inventory(db, reservation_id)
        if not confirmed:
            db.rollback()
            return False, "inventory_confirm_failed", None, None

        # Apply coupon
        discount_amount = 0.0
        if coupon_code:
            coupon = db.query(Coupon).filter(
                Coupon.code == coupon_code, Coupon.status == "ACTIVE"
            ).first()
            if coupon and coupon.used_count < coupon.max_usage:
                if coupon.discount_type == "PERCENTAGE":
                    discount_amount = round(amount * float(coupon.discount_value) / 100, 2)
                else:
                    discount_amount = min(float(coupon.discount_value), amount)
                coupon.used_count += 1

        final_amount = max(0.0, amount - discount_amount)

        order = _create_order_sync(
            db, reservation, final_amount, discount_amount, coupon_code,
            json.dumps(shipping_address) if shipping_address else None
        )

        # Create shipment
        shipment = Shipment(
            shipment_id=str(uuid.uuid4()),
            order_id=order.order_id,
            tracking_number=f"SS{str(uuid.uuid4())[:8].upper()}",
            carrier=random.choice(CARRIERS),
            status="CREATED",
            estimated_delivery=datetime.utcnow() + timedelta(days=random.randint(3, 7)),
        )
        db.add(shipment)

        # Create notification
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            customer_id=customer_id,
            order_id=order.order_id,
            notification_type="ORDER_CONFIRMED",
            title="Order Confirmed! 🎉",
            message=f"Your order #{order.order_id[:8].upper()} has been confirmed. Total: ₹{final_amount:,.0f}",
            is_read=False,
            status="SENT",
        )
        db.add(notification)

        payment = Payment(
            payment_id=str(uuid.uuid4()),
            customer_id=customer_id,
            amount=final_amount,
            payment_reference=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            status="SUCCESS",
            payment_method=payment_method,
            order_id=order.order_id,
        )
        db.add(payment)
        payment_success_total.inc()
        db.commit()
        db.refresh(payment)
        db.refresh(order)

        await publish_event(STREAM_PAYMENTS, "PaymentSucceeded", {
            "payment_id": payment.payment_id,
            "reservation_id": reservation_id,
            "customer_id": customer_id,
            "amount": final_amount,
            "order_id": order.order_id,
        })
        await publish_event(STREAM_ORDERS, "OrderCreated", {
            "order_id": order.order_id,
            "customer_id": customer_id,
            "reservation_id": reservation_id,
            "total_amount": final_amount,
        })
        logger.info("payment_success", payment_id=payment.payment_id, order_id=order.order_id)
        return True, "SUCCESS", payment, order

    elif outcome == "FAILED":
        payment = Payment(
            payment_id=str(uuid.uuid4()),
            customer_id=customer_id,
            amount=amount,
            payment_reference=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            status="FAILED",
            payment_method=payment_method,
        )
        db.add(payment)

        notification = Notification(
            notification_id=str(uuid.uuid4()),
            customer_id=customer_id,
            notification_type="PAYMENT_FAILED",
            title="Payment Failed ❌",
            message="Your payment could not be processed. Your reservation has been released.",
            is_read=False,
            status="SENT",
        )
        db.add(notification)
        db.commit()
        db.refresh(payment)

        release_inventory(db, reservation_id, new_status="PAYMENT_FAILED")
        payment_failure_total.inc()

        await publish_event(STREAM_PAYMENTS, "PaymentFailed", {
            "payment_id": payment.payment_id,
            "reservation_id": reservation_id,
            "customer_id": customer_id,
        })
        logger.info("payment_failed", payment_id=payment.payment_id)
        return False, "FAILED", payment, None

    else:  # TIMEOUT
        reservation.status = "PAYMENT_PENDING"
        reservation.updated_at = datetime.utcnow()

        payment = Payment(
            payment_id=str(uuid.uuid4()),
            customer_id=customer_id,
            amount=amount,
            payment_reference=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            status="TIMEOUT",
            payment_method=payment_method,
        )
        db.add(payment)
        payment_timeout_total.inc()
        db.commit()
        db.refresh(payment)

        await publish_event(STREAM_PAYMENTS, "PaymentTimeout", {
            "payment_id": payment.payment_id,
            "reservation_id": reservation_id,
            "customer_id": customer_id,
        })
        logger.warning("payment_timeout", payment_id=payment.payment_id)
        return False, "TIMEOUT", payment, None


def _create_order_sync(
    db: Session,
    reservation: Reservation,
    total_amount: float,
    discount_amount: float = 0.0,
    coupon_code: str = None,
    shipping_address: str = None,
) -> Order:
    idempotency_key = f"order-{reservation.reservation_id}"
    existing = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
    if existing:
        return existing

    product = db.query(Product).filter(Product.product_id == reservation.product_id).first()
    sale = (
        db.query(Sale)
        .filter(Sale.product_id == reservation.product_id, Sale.status == "ACTIVE")
        .first()
    )
    unit_price = float(sale.sale_price) if sale else float(product.price)

    order = Order(
        order_id=str(uuid.uuid4()),
        customer_id=reservation.customer_id,
        reservation_id=reservation.reservation_id,
        total_amount=total_amount,
        discount_amount=discount_amount,
        coupon_code=coupon_code,
        status="CONFIRMED",
        shipping_address=shipping_address,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_item_id=str(uuid.uuid4()),
        order_id=order.order_id,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        unit_price=unit_price,
        subtotal=unit_price * reservation.quantity,
    )
    db.add(order_item)
    db.flush()

    orders_created_total.inc()
    return order


def get_payment(db: Session, payment_id: str) -> Payment | None:
    return db.query(Payment).filter(Payment.payment_id == payment_id).first()


def _determine_outcome(simulate_outcome: str | None) -> str:
    if simulate_outcome in ("SUCCESS", "FAILED", "TIMEOUT"):
        return simulate_outcome
    roll = random.random()
    if roll < 0.85:
        return "SUCCESS"
    elif roll < 0.95:
        return "FAILED"
    else:
        return "TIMEOUT"
