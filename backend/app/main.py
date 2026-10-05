"""
SALESTORM – High-Scale Flash Sale System
Main FastAPI application entry point.
"""
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.metrics import http_requests_total, http_request_duration

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("salestorm_starting", environment=settings.environment)
    try:
        from app.core.init_db import init_db
        init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    yield
    try:
        from app.core.redis_client import close_redis
        await close_redis()
    except Exception:
        pass
    logger.info("salestorm_shutdown")


app = FastAPI(
    title="SALESTORM",
    description="High-Scale Flash Sale System — 10,000 users, 100 units, zero overselling.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start

    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)

    try:
        http_requests_total.labels(method=method, endpoint=endpoint, status_code=status).inc()
        http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    except Exception:
        pass

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http_request",
        method=method,
        path=endpoint,
        status_code=status,
        duration_ms=round(duration * 1000, 2),
    )
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
from app.api import products, sale, reservations, checkout, payments, orders, admin
from app.api import auth, cart, notifications, shipments

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(sale.router)
app.include_router(reservations.router)
app.include_router(checkout.router)
app.include_router(payments.router)
app.include_router(orders.router)
app.include_router(shipments.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"status": "ok", "service": "salestorm", "version": "2.0.0"}


@app.get("/")
def root():
    return {
        "service": "SALESTORM",
        "description": "High-Scale Flash Sale System",
        "docs": "/docs",
        "metrics": "/metrics",
        "health": "/health",
    }
