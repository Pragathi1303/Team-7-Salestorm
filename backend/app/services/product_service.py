"""
Product service with Redis caching for read-heavy product data.
PostgreSQL remains the source of truth for inventory.
Gracefully degrades when Redis is unavailable.
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Product, Sale, Inventory, Category
from app.core.logging import get_logger

logger = get_logger(__name__)

CACHE_TTL = 60
PRODUCT_CACHE_PREFIX = "cache:product"
SALE_CACHE_PREFIX = "cache:sale"


async def get_product_cached(db: Session, product_id: str) -> dict | None:
    try:
        from app.core.redis_client import get_async_redis
        redis = get_async_redis()
        cache_key = f"{PRODUCT_CACHE_PREFIX}:{product_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return None

    data = {
        "product_id": product.product_id,
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "sku": product.sku,
        "status": product.status,
        "category_id": product.category_id,
    }

    try:
        from app.core.redis_client import get_async_redis
        redis = get_async_redis()
        await redis.setex(f"{PRODUCT_CACHE_PREFIX}:{product_id}", CACHE_TTL, json.dumps(data))
    except Exception:
        pass

    return data


async def get_active_sale_for_product(db: Session, product_id: str) -> dict | None:
    try:
        from app.core.redis_client import get_async_redis
        redis = get_async_redis()
        cache_key = f"{SALE_CACHE_PREFIX}:{product_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

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
        return None

    data = {
        "sale_id": sale.sale_id,
        "sale_name": sale.sale_name,
        "sale_price": float(sale.sale_price),
        "end_time": sale.end_time.isoformat(),
        "status": sale.status,
    }

    try:
        from app.core.redis_client import get_async_redis
        redis = get_async_redis()
        await redis.setex(f"{SALE_CACHE_PREFIX}:{product_id}", CACHE_TTL, json.dumps(data))
    except Exception:
        pass

    return data


def get_all_products(db: Session) -> list[Product]:
    return db.query(Product).filter(Product.status == "ACTIVE").all()


def get_inventory(db: Session, product_id: str) -> Inventory | None:
    return db.query(Inventory).filter(Inventory.product_id == product_id).first()


async def invalidate_product_cache(product_id: str):
    try:
        from app.core.redis_client import get_async_redis
        redis = get_async_redis()
        await redis.delete(f"{PRODUCT_CACHE_PREFIX}:{product_id}")
        await redis.delete(f"{SALE_CACHE_PREFIX}:{product_id}")
    except Exception:
        pass
