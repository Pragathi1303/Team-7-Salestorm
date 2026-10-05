from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Use default registry
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

queue_length = Gauge("queue_length", "Current virtual queue length")

reservation_success_total = Counter(
    "reservation_success_total", "Successful reservations"
)
reservation_failure_total = Counter(
    "reservation_failure_total", "Failed reservations", ["reason"]
)
reservation_expired_total = Counter(
    "reservation_expired_total", "Expired reservations"
)

payment_success_total = Counter("payment_success_total", "Successful payments")
payment_failure_total = Counter("payment_failure_total", "Failed payments")
payment_timeout_total = Counter("payment_timeout_total", "Timed out payments")

orders_created_total = Counter("orders_created_total", "Orders created")

inventory_available = Gauge(
    "inventory_available", "Available inventory", ["product_id"]
)
inventory_reserved = Gauge(
    "inventory_reserved", "Reserved inventory", ["product_id"]
)
inventory_sold = Gauge("inventory_sold", "Sold inventory", ["product_id"])

oversold_units = Gauge("oversold_units", "Oversold units (must always be 0)")

duplicate_requests_total = Counter(
    "duplicate_requests_total", "Duplicate idempotent requests", ["type"]
)
