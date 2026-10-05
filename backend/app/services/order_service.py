"""
Order service.
Creates and manages orders. Idempotent — safe to call multiple times.
Recovers from event replay if Order Service was temporarily unavailable.
"""
from sqlalchemy.orm import Session
from app.models.models import Order, OrderItem
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_order(db: Session, order_id: str) -> Order | None:
    return (
        db.query(Order)
        .filter(Order.order_id == order_id)
        .first()
    )


def get_order_with_items(db: Session, order_id: str) -> Order | None:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order:
        # Eagerly load items
        _ = order.items
    return order


def advance_order_status(db: Session, order_id: str, new_status: str) -> Order | None:
    """Advance order through its lifecycle."""
    valid_transitions = {
        "CREATED": ["PAYMENT_PENDING", "CONFIRMED"],
        "PAYMENT_PENDING": ["CONFIRMED"],
        "CONFIRMED": ["PROCESSING"],
        "PROCESSING": ["SHIPPED"],
        "SHIPPED": ["OUT_FOR_DELIVERY"],
        "OUT_FOR_DELIVERY": ["DELIVERED"],
    }
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return None
    if new_status not in valid_transitions.get(order.status, []):
        logger.warning(
            "invalid_order_transition",
            order_id=order_id,
            current=order.status,
            requested=new_status,
        )
        return order

    from datetime import datetime
    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    logger.info("order_status_advanced", order_id=order_id, status=new_status)
    return order
