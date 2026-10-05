"""
Event Consumer Worker.
Reads from Redis Streams and processes events.
Implements retry logic and dead-letter queue.
Idempotent: safe to process the same event multiple times.
"""
import json
import time
import uuid
from datetime import datetime

from app.core.redis_client import get_sync_redis
from app.core.database import SessionLocal
from app.core.event_bus import (
    STREAM_ORDERS, STREAM_SHIPMENTS, STREAM_NOTIFICATIONS, STREAM_ANALYTICS,
    GROUP_ORDER_CONSUMER, GROUP_SHIPMENT_CONSUMER,
    GROUP_NOTIFICATION_CONSUMER, GROUP_ANALYTICS_CONSUMER,
    ensure_consumer_groups, send_to_dlq, MAX_RETRY_COUNT
)
from app.core.logging import get_logger
from app.models.models import Order, Shipment, Notification
from app.services.order_service import advance_order_status

logger = get_logger(__name__)
CONSUMER_ID = f"consumer-{str(uuid.uuid4())[:8]}"


def process_order_event(db, event_type: str, payload: dict):
    """Handle order-related events. Idempotent."""
    if event_type == "OrderCreated":
        order_id = payload.get("order_id")
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order and order.status == "CONFIRMED":
            advance_order_status(db, order_id, "PROCESSING")
            logger.info("order_processing_started", order_id=order_id)

    elif event_type == "PaymentSucceeded":
        order_id = payload.get("order_id")
        if order_id:
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if order and order.status == "CREATED":
                advance_order_status(db, order_id, "CONFIRMED")


def process_shipment_event(db, event_type: str, payload: dict):
    """Handle shipment events. Idempotent."""
    if event_type == "OrderCreated":
        order_id = payload.get("order_id")
        # Check if shipment already exists (idempotency)
        existing = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if existing:
            return

        shipment = Shipment(
            shipment_id=str(uuid.uuid4()),
            order_id=order_id,
            tracking_number=f"TRK-{str(uuid.uuid4())[:12].upper()}",
            carrier="MOCK_CARRIER",
            status="PENDING",
        )
        db.add(shipment)
        db.commit()
        logger.info("shipment_created", order_id=order_id, shipment_id=shipment.shipment_id)


def process_notification_event(db, event_type: str, payload: dict):
    """Handle notification events. Idempotent."""
    customer_id = payload.get("customer_id")
    order_id = payload.get("order_id")

    if not customer_id:
        return

    # Check if notification already sent (idempotency)
    existing = db.query(Notification).filter(
        Notification.customer_id == customer_id,
        Notification.notification_type == event_type,
        Notification.order_id == order_id,
    ).first()
    if existing:
        return

    messages = {
        "PaymentSucceeded": "Your payment was successful! Your order is confirmed.",
        "PaymentFailed": "Your payment failed. Your reservation has been released.",
        "OrderCreated": "Your order has been created and is being processed.",
        "ReservationCreated": "You've successfully reserved your item!",
        "ReservationExpired": "Your reservation has expired.",
    }
    message = messages.get(event_type, f"Event: {event_type}")

    notification = Notification(
        notification_id=str(uuid.uuid4()),
        customer_id=customer_id,
        order_id=order_id,
        notification_type=event_type,
        channel="EMAIL",
        message=message,
        status="SENT",
        sent_at=datetime.utcnow(),
    )
    db.add(notification)
    db.commit()
    logger.info("notification_sent", customer_id=customer_id, type=event_type)


def process_analytics_event(db, event_type: str, payload: dict):
    """Analytics consumer — logs events for metrics."""
    logger.info("analytics_event", event_type=event_type, payload=payload)


def consume_stream(redis, stream: str, group: str, handler):
    """Read and process messages from a Redis Stream consumer group."""
    try:
        messages = redis.xreadgroup(
            groupname=group,
            consumername=CONSUMER_ID,
            streams={stream: ">"},
            count=10,
            block=1000,  # 1 second block
        )
    except Exception as e:
        logger.error("stream_read_error", stream=stream, error=str(e))
        return

    if not messages:
        return

    for stream_name, msg_list in messages:
        for msg_id, msg_data in msg_list:
            retry_count = int(msg_data.get("retry_count", 0))
            event_type = msg_data.get("event_type", "")
            payload_str = msg_data.get("payload", "{}")

            try:
                payload = json.loads(payload_str)
                db = SessionLocal()
                try:
                    handler(db, event_type, payload)
                    redis.xack(stream, group, msg_id)
                    logger.info("event_processed", stream=stream, event_type=event_type, msg_id=msg_id)
                finally:
                    db.close()

            except Exception as e:
                logger.error("event_processing_error", stream=stream, msg_id=msg_id, error=str(e))
                if retry_count >= MAX_RETRY_COUNT:
                    send_to_dlq(redis, stream, msg_id, msg_data, str(e))
                    redis.xack(stream, group, msg_id)
                else:
                    # Re-add with incremented retry count
                    updated = dict(msg_data)
                    updated["retry_count"] = str(retry_count + 1)
                    redis.xadd(stream, updated)
                    redis.xack(stream, group, msg_id)


def run():
    """Main worker loop."""
    redis = get_sync_redis()
    ensure_consumer_groups(redis)

    logger.info("event_consumer_started", consumer_id=CONSUMER_ID)

    stream_handlers = [
        (STREAM_ORDERS, GROUP_ORDER_CONSUMER, process_order_event),
        (STREAM_ORDERS, GROUP_SHIPMENT_CONSUMER, process_shipment_event),
        (STREAM_ORDERS, GROUP_NOTIFICATION_CONSUMER, process_notification_event),
        (STREAM_ORDERS, GROUP_ANALYTICS_CONSUMER, process_analytics_event),
    ]

    while True:
        for stream, group, handler in stream_handlers:
            consume_stream(redis, stream, group, handler)
        time.sleep(0.1)


if __name__ == "__main__":
    run()
