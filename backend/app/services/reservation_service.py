"""
Reservation service.
Orchestrates: inventory allocation → reservation creation → event publishing.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.inventory_allocator import allocate_inventory, release_inventory
from app.core.event_bus import publish_event, STREAM_RESERVATIONS
from app.core.metrics import (
    reservation_success_total, reservation_failure_total, duplicate_requests_total
)
from app.models.models import Reservation, Product, Sale
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_reservation(
    db: Session,
    customer_id: str,
    product_id: str,
    quantity: int,
    idempotency_key: str,
) -> tuple[bool, str, "Reservation | None"]:
    """
    Main reservation flow:
    1. Validate product and active sale.
    2. Allocate inventory atomically (SELECT FOR UPDATE).
    3. Publish ReservationCreated event (best-effort).
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product or product.status != "ACTIVE":
        reservation_failure_total.labels(reason="invalid_product").inc()
        return False, "product_not_found_or_inactive", None

    now = datetime.utcnow()
    sale = (
        db.query(Sale)
        .filter(
            Sale.product_id == product_id,
            Sale.status == "ACTIVE",
            Sale.start_time <= now,
            Sale.end_time >= now,
        )
        .first()
    )
    if not sale:
        reservation_failure_total.labels(reason="no_active_sale").inc()
        return False, "no_active_sale", None

    success, message, reservation = allocate_inventory(
        db=db,
        product_id=product_id,
        customer_id=customer_id,
        quantity=quantity,
        idempotency_key=idempotency_key,
    )

    if not success:
        reason = "out_of_stock" if message == "out_of_stock" else "allocation_error"
        reservation_failure_total.labels(reason=reason).inc()
        return False, message, None

    if message == "existing_reservation":
        duplicate_requests_total.labels(type="reservation").inc()
        return True, "existing_reservation", reservation

    reservation_success_total.inc()

    # Publish event — best-effort, never blocks the response
    await publish_event(
        STREAM_RESERVATIONS,
        "ReservationCreated",
        {
            "reservation_id": reservation.reservation_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "expires_at": reservation.expires_at.isoformat(),
        },
    )

    return True, "reserved", reservation


def get_reservation(db: Session, reservation_id: str) -> "Reservation | None":
    return db.query(Reservation).filter(
        Reservation.reservation_id == reservation_id
    ).first()


async def cancel_reservation(
    db: Session, reservation_id: str, customer_id: str
) -> bool:
    reservation = get_reservation(db, reservation_id)
    if not reservation or reservation.customer_id != customer_id:
        return False
    if reservation.status not in ("RESERVED", "PAYMENT_PENDING"):
        return False

    released = release_inventory(db, reservation_id, new_status="RELEASED")
    if released:
        await publish_event(
            STREAM_RESERVATIONS,
            "ReservationCancelled",
            {"reservation_id": reservation_id, "customer_id": customer_id},
        )
    return released
