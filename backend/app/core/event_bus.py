"""
Redis Streams event bus.
Producers publish events; consumers read from streams with consumer groups.
Dead-letter queue for repeatedly failed messages.
Gracefully no-ops when Redis is unavailable (e.g. during tests).
"""
import json
import uuid
from datetime import datetime
from app.core.redis_client import get_async_redis, get_sync_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

STREAM_RESERVATIONS = "stream:reservations"
STREAM_PAYMENTS = "stream:payments"
STREAM_ORDERS = "stream:orders"
STREAM_SHIPMENTS = "stream:shipments"
STREAM_NOTIFICATIONS = "stream:notifications"
STREAM_ANALYTICS = "stream:analytics"
STREAM_DLQ = "stream:dlq"

GROUP_ORDER_CONSUMER = "order-consumer-group"
GROUP_SHIPMENT_CONSUMER = "shipment-consumer-group"
GROUP_NOTIFICATION_CONSUMER = "notification-consumer-group"
GROUP_ANALYTICS_CONSUMER = "analytics-consumer-group"

MAX_RETRY_COUNT = 3


async def publish_event(stream: str, event_type: str, payload: dict) -> str:
    """Publish an event to a Redis Stream. No-ops gracefully if Redis is down."""
    try:
        redis = get_async_redis()
        message = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": json.dumps(payload),
        }
        msg_id = await redis.xadd(stream, message)
        logger.info("event_published", stream=stream, event_type=event_type, msg_id=msg_id)
        return msg_id
    except Exception as e:
        logger.warning("event_publish_failed", stream=stream, event_type=event_type, error=str(e))
        return ""


def publish_event_sync(stream: str, event_type: str, payload: dict) -> str:
    """Synchronous version for workers."""
    try:
        redis = get_sync_redis()
        message = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": json.dumps(payload),
        }
        msg_id = redis.xadd(stream, message)
        logger.info("event_published_sync", stream=stream, event_type=event_type, msg_id=msg_id)
        return msg_id
    except Exception as e:
        logger.warning("event_publish_sync_failed", stream=stream, event_type=event_type, error=str(e))
        return ""


def ensure_consumer_groups(redis):
    """Create consumer groups if they don't exist. Idempotent."""
    groups = [
        (STREAM_ORDERS, GROUP_ORDER_CONSUMER),
        (STREAM_SHIPMENTS, GROUP_SHIPMENT_CONSUMER),
        (STREAM_NOTIFICATIONS, GROUP_NOTIFICATION_CONSUMER),
        (STREAM_ANALYTICS, GROUP_ANALYTICS_CONSUMER),
    ]
    for stream, group in groups:
        try:
            redis.xgroup_create(stream, group, id="0", mkstream=True)
            logger.info("consumer_group_created", stream=stream, group=group)
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.warning("consumer_group_create_error", stream=stream, group=group, error=str(e))


def send_to_dlq(redis, stream: str, msg_id: str, message: dict, error: str):
    """Move a failed message to the dead-letter queue."""
    try:
        dlq_entry = {
            "original_stream": stream,
            "original_msg_id": msg_id,
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
            **message,
        }
        redis.xadd(STREAM_DLQ, dlq_entry)
        logger.warning("message_sent_to_dlq", stream=stream, msg_id=msg_id, error=error)
    except Exception as e:
        logger.error("dlq_write_failed", error=str(e))
