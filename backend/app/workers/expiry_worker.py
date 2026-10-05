"""
Reservation Expiry Worker.
Periodically scans for expired reservations and releases their inventory.
Publishes ReservationExpired events.
"""
import time
from datetime import datetime

from app.core.database import SessionLocal
from app.core.event_bus import publish_event_sync, STREAM_RESERVATIONS
from app.core.inventory_allocator import release_inventory
from app.core.metrics import reservation_expired_total
from app.models.models import Reservation
from app.core.logging import get_logger

logger = get_logger(__name__)
SCAN_INTERVAL_SECONDS = 5


def expire_reservations():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = (
            db.query(Reservation)
            .filter(
                Reservation.status.in_(["RESERVED", "PAYMENT_PENDING"]),
                Reservation.expires_at < now,
            )
            .all()
        )

        for reservation in expired:
            rid = reservation.reservation_id
            cid = reservation.customer_id
            pid = reservation.product_id
            qty = reservation.quantity

            # release_inventory handles status transition atomically
            released = release_inventory(db, rid, new_status="EXPIRED")
            if released:
                reservation_expired_total.inc()
                publish_event_sync(
                    STREAM_RESERVATIONS,
                    "ReservationExpired",
                    {
                        "reservation_id": rid,
                        "customer_id": cid,
                        "product_id": pid,
                        "quantity": qty,
                    },
                )
                logger.info("reservation_expired", reservation_id=rid, customer_id=cid)

        if expired:
            logger.info("expiry_scan_complete", expired_count=len(expired))

    except Exception as e:
        logger.error("expiry_worker_error", error=str(e))
        db.rollback()
    finally:
        db.close()


def run():
    logger.info("expiry_worker_started")
    while True:
        expire_reservations()
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
