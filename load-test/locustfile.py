"""
SALESTORM Load Test — Locust
Scenario: 10,000 concurrent users, 100 units, zero overselling.

Run:
    locust -f locustfile.py --host=http://localhost:8000 \
           --users=10000 --spawn-rate=500 --run-time=60s --headless

Environment variables:
    LOCUST_USERS=10000
    LOCUST_SPAWN_RATE=500
    LOCUST_RUN_TIME=60s
    TARGET_PRODUCT_SKU=P001
    TARGET_HOST=http://localhost:8000
"""
import uuid
import os
import json
import threading
from locust import HttpUser, task, events, constant_pacing
from locust.runners import MasterRunner, WorkerRunner

TARGET_HOST = os.getenv("TARGET_HOST", "http://localhost:8000")
TARGET_PRODUCT_SKU = os.getenv("TARGET_PRODUCT_SKU", "P001")

# Shared counters (thread-safe)
_lock = threading.Lock()
_stats = {
    "total_attempts": 0,
    "successful_reservations": 0,
    "rejected_out_of_stock": 0,
    "rejected_other": 0,
    "duplicate_reservations": 0,
    "payment_success": 0,
    "payment_failure": 0,
    "errors": 0,
}


def inc(key, amount=1):
    with _lock:
        _stats[key] += amount


class FlashSaleUser(HttpUser):
    """
    Simulates a single user attempting to purchase during a flash sale.
    Each user:
    1. Fetches product info
    2. Joins the virtual queue
    3. Attempts a reservation (direct, bypassing queue wait for load test speed)
    4. If successful, proceeds to payment
    """
    wait_time = constant_pacing(1)  # 1 request per second per user

    def on_start(self):
        """Called once per user on startup — create a unique customer."""
        self.customer_id = None
        self.product_id = None
        self.sale_id = None
        self.reservation_id = None

        # Create a demo customer
        resp = self.client.post(
            "/api/admin/customers/demo",
            headers={"x-admin-key": "admin-demo-key"},
            name="/api/admin/customers/demo",
        )
        if resp.status_code == 201:
            data = resp.json()
            self.customer_id = data.get("customer_id")

        # Fetch product
        resp = self.client.get("/api/products", name="/api/products")
        if resp.status_code == 200:
            products = resp.json()
            for p in products:
                if p.get("sku") == TARGET_PRODUCT_SKU:
                    self.product_id = p["product_id"]
                    self.sale_id = p.get("sale_id")
                    break

    @task
    def purchase_flow(self):
        if not self.customer_id or not self.product_id:
            return

        inc("total_attempts")
        idem_key = str(uuid.uuid4())

        # Direct reservation (bypasses queue wait for load test throughput)
        resp = self.client.post(
            "/api/reservations",
            json={
                "customer_id": self.customer_id,
                "product_id": self.product_id,
                "quantity": 1,
                "idempotency_key": idem_key,
            },
            name="/api/reservations",
        )

        if resp.status_code == 201:
            data = resp.json()
            self.reservation_id = data["reservation_id"]

            # Check if this was a duplicate
            if data.get("status") == "RESERVED":
                inc("successful_reservations")
            else:
                inc("duplicate_reservations")

            # Proceed to payment
            self._do_payment()

        elif resp.status_code == 409:
            inc("rejected_out_of_stock")
        elif resp.status_code == 400:
            body = resp.json()
            if "out_of_stock" in str(body):
                inc("rejected_out_of_stock")
            else:
                inc("rejected_other")
        else:
            inc("errors")

    def _do_payment(self):
        if not self.reservation_id:
            return

        # Get checkout info first
        resp = self.client.post(
            "/api/checkout",
            json={
                "reservation_id": self.reservation_id,
                "customer_id": self.customer_id,
            },
            name="/api/checkout",
        )
        if resp.status_code != 200:
            return

        checkout = resp.json()
        amount = checkout["total_amount"]

        # Process payment (simulate SUCCESS for load test)
        pay_resp = self.client.post(
            "/api/payments",
            json={
                "reservation_id": self.reservation_id,
                "customer_id": self.customer_id,
                "amount": amount,
                "payment_method": "MOCK",
                "idempotency_key": str(uuid.uuid4()),
                "simulate_outcome": "SUCCESS",
            },
            name="/api/payments",
        )

        if pay_resp.status_code == 201:
            data = pay_resp.json()
            if data["status"] == "SUCCESS":
                inc("payment_success")
            else:
                inc("payment_failure")
        else:
            inc("payment_failure")


class QueueFlowUser(HttpUser):
    """
    Tests the full queue flow: join → poll → reserve.
    Use this for realistic queue behavior testing.
    """
    wait_time = constant_pacing(2)

    def on_start(self):
        self.customer_id = None
        self.product_id = None
        self.sale_id = None

        resp = self.client.post(
            "/api/admin/customers/demo",
            headers={"x-admin-key": "admin-demo-key"},
            name="/api/admin/customers/demo [setup]",
        )
        if resp.status_code == 201:
            self.customer_id = resp.json().get("customer_id")

        resp = self.client.get("/api/products", name="/api/products [setup]")
        if resp.status_code == 200:
            for p in resp.json():
                if p.get("sku") == TARGET_PRODUCT_SKU:
                    self.product_id = p["product_id"]
                    self.sale_id = p.get("sale_id")
                    break

    @task
    def queue_and_reserve(self):
        if not self.customer_id or not self.product_id or not self.sale_id:
            return

        idem_key = str(uuid.uuid4())

        # Step 1: Join queue
        resp = self.client.post(
            "/api/sale/join",
            json={
                "sale_id": self.sale_id,
                "customer_id": self.customer_id,
                "product_id": self.product_id,
                "quantity": 1,
                "idempotency_key": idem_key,
            },
            name="/api/sale/join",
        )
        if resp.status_code != 200:
            return

        queue_token = resp.json().get("queue_token")

        # Step 2: Poll queue status
        self.client.get(
            f"/api/sale/queue/{queue_token}",
            name="/api/sale/queue/{token}",
        )

        # Step 3: Attempt reservation
        self.client.post(
            "/api/reservations",
            json={
                "customer_id": self.customer_id,
                "product_id": self.product_id,
                "quantity": 1,
                "idempotency_key": idem_key,
                "queue_token": queue_token,
            },
            name="/api/reservations [queued]",
        )


# ── Event hooks for final report ──────────────────────────────────────────────

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "=" * 60)
    print("SALESTORM LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total Attempts:            {_stats['total_attempts']}")
    print(f"Successful Reservations:   {_stats['successful_reservations']}")
    print(f"Rejected (Out of Stock):   {_stats['rejected_out_of_stock']}")
    print(f"Rejected (Other):          {_stats['rejected_other']}")
    print(f"Duplicate Reservations:    {_stats['duplicate_reservations']}")
    print(f"Payment Success:           {_stats['payment_success']}")
    print(f"Payment Failure:           {_stats['payment_failure']}")
    print(f"Errors:                    {_stats['errors']}")
    print("-" * 60)

    initial_inventory = int(os.getenv("DEMO_INITIAL_INVENTORY", 100))
    oversold = max(0, _stats["successful_reservations"] - initial_inventory)
    print(f"Initial Inventory:         {initial_inventory}")
    print(f"OVERSOLD UNITS:            {oversold}  ← MUST BE 0")
    print("=" * 60)

    if oversold > 0:
        print("❌ OVERSELLING DETECTED — ARCHITECTURE FAILURE")
    else:
        print("✅ NO OVERSELLING — ARCHITECTURE CORRECT")

    assert _stats["successful_reservations"] <= initial_inventory, (
        f"OVERSELL: {_stats['successful_reservations']} reservations > {initial_inventory} inventory"
    )
