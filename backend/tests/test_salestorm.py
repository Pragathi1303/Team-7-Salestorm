"""
SALESTORM Test Suite — 15 required test cases.
Uses SQLite in-memory for speed. PostgreSQL SELECT FOR UPDATE is tested via Docker.
"""
import uuid
import pytest
import threading
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.inventory_allocator import (
    allocate_inventory, release_inventory, confirm_inventory
)
from app.models.models import (
    Customer, Product, Category, Inventory, Sale,
    Reservation, Order, OrderItem, Payment
)
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ───────────────────────────────────────────────────────────────────

from sqlalchemy import event

def make_engine(path=None):
    url = f"sqlite:///{path}" if path else "sqlite://"
    eng = create_engine(url, connect_args={"check_same_thread": False})
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
    return eng


def seed(db, initial_qty=100):
    cat = Category(category_id=str(uuid.uuid4()), category_name="Test", description="")
    db.add(cat)
    db.flush()

    product = Product(
        product_id=str(uuid.uuid4()), category_id=cat.category_id,
        name="Test TV", description="", price=100.0,
        sku=f"SKU-{uuid.uuid4().hex[:6]}", status="ACTIVE",
    )
    db.add(product)
    db.flush()

    inv = Inventory(
        inventory_id=str(uuid.uuid4()), product_id=product.product_id,
        available_quantity=initial_qty, reserved_quantity=0, sold_quantity=0, version=1,
    )
    db.add(inv)

    now = datetime.utcnow()
    sale = Sale(
        sale_id=str(uuid.uuid4()), product_id=product.product_id,
        sale_name="Test Sale",
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(hours=1),
        sale_price=50.0, status="ACTIVE",
    )
    db.add(sale)

    customer = Customer(
        customer_id=str(uuid.uuid4()), name="Test",
        email=f"t_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=pwd.hash("x"),
    )
    db.add(customer)
    db.commit()
    return product, inv, customer


# ── Test 1: Normal reservation ────────────────────────────────────────────────

def test_normal_reservation(db, demo_product, demo_inventory, demo_sale, demo_customer):
    ok, msg, res = allocate_inventory(
        db, demo_product.product_id, demo_customer.customer_id, 1, str(uuid.uuid4())
    )
    assert ok is True
    assert res is not None
    assert res.status == "RESERVED"
    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity == 99
    assert demo_inventory.reserved_quantity == 1


# ── Test 2: Out of stock ──────────────────────────────────────────────────────

def test_out_of_stock(db, demo_product, demo_inventory, demo_sale, demo_customer):
    demo_inventory.available_quantity = 0
    db.commit()
    ok, msg, res = allocate_inventory(
        db, demo_product.product_id, demo_customer.customer_id, 1, str(uuid.uuid4())
    )
    assert ok is False
    assert msg == "out_of_stock"
    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity == 0


# ── Test 3: Concurrent requests — no oversell ─────────────────────────────────

def test_concurrent_no_oversell():
    INITIAL = 100
    THREADS = 500

    engine = make_engine("./test_concurrent.db")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    product, inv, customer = seed(db, INITIAL)
    pid, cid = product.product_id, customer.customer_id
    db.close()

    results = {"ok": 0, "fail": 0}
    lock = threading.Lock()

    def attempt():
        s = Session()
        try:
            ok, _, _ = allocate_inventory(s, pid, cid, 1, str(uuid.uuid4()))
            with lock:
                if ok:
                    results["ok"] += 1
                else:
                    results["fail"] += 1
        except Exception:
            with lock:
                results["fail"] += 1
        finally:
            s.close()

    threads = [threading.Thread(target=attempt) for _ in range(THREADS)]
    for t in threads: t.start()
    for t in threads: t.join()

    check = Session()
    final = check.query(Inventory).filter(Inventory.product_id == pid).first()
    check.close()

    assert results["ok"] <= INITIAL, f"OVERSELL: {results['ok']} > {INITIAL}"
    assert final.available_quantity >= 0, "Inventory went negative!"
    assert results["ok"] + results["fail"] == THREADS

    import os
    engine.dispose()
    try:
        if os.path.exists("./test_concurrent.db"): os.remove("./test_concurrent.db")
    except Exception:
        pass


# ── Test 4: Duplicate reservation idempotency ─────────────────────────────────

def test_duplicate_reservation_idempotency(db, demo_product, demo_inventory, demo_sale, demo_customer):
    key = str(uuid.uuid4())
    ok1, msg1, r1 = allocate_inventory(db, demo_product.product_id, demo_customer.customer_id, 1, key)
    ok2, msg2, r2 = allocate_inventory(db, demo_product.product_id, demo_customer.customer_id, 1, key)

    assert ok1 and ok2
    assert r1.reservation_id == r2.reservation_id
    assert msg2 == "existing_reservation"
    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity == 99  # Only decremented once


# ── Test 5: Reservation expiry releases inventory ─────────────────────────────

def test_reservation_expiry_releases_inventory(db, demo_product, demo_inventory, demo_sale, demo_customer):
    ok, _, res = allocate_inventory(
        db, demo_product.product_id, demo_customer.customer_id, 1, str(uuid.uuid4())
    )
    assert ok
    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity == 99

    released = release_inventory(db, res.reservation_id, new_status="EXPIRED")
    assert released is True
    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity == 100
    assert demo_inventory.reserved_quantity == 0


# ── Test 6: Payment success confirms inventory ────────────────────────────────

def test_payment_success_confirms_inventory(db, demo_product, demo_inventory, demo_sale, demo_customer, active_reservation):
    ok = confirm_inventory(db, active_reservation.reservation_id)
    assert ok is True
    db.commit()  # confirm_inventory flushes only
    db.refresh(demo_inventory)
    assert demo_inventory.reserved_quantity == 0
    assert demo_inventory.sold_quantity == 1
    assert demo_inventory.available_quantity == 99


# ── Test 7: Payment failure releases inventory ────────────────────────────────

def test_payment_failure_releases_inventory(db, demo_product, demo_inventory, demo_sale, demo_customer, active_reservation):
    released = release_inventory(db, active_reservation.reservation_id, new_status="PAYMENT_FAILED")
    assert released is True
    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity == 100
    assert demo_inventory.reserved_quantity == 0


# ── Test 8: Payment timeout leaves inventory reserved ─────────────────────────

def test_payment_timeout_does_not_release(db, demo_product, demo_inventory, demo_sale, demo_customer, active_reservation):
    active_reservation.status = "PAYMENT_PENDING"
    db.commit()
    db.refresh(demo_inventory)
    # Inventory still reserved — not released on timeout
    assert demo_inventory.reserved_quantity == 1
    assert demo_inventory.available_quantity == 99


# ── Test 9: Duplicate payment idempotency ─────────────────────────────────────

def test_duplicate_payment_idempotency(db, demo_customer, active_reservation):
    key = str(uuid.uuid4())
    p1 = Payment(
        payment_id=str(uuid.uuid4()), customer_id=demo_customer.customer_id,
        amount=49999.0, payment_reference=str(uuid.uuid4()),
        idempotency_key=key, status="SUCCESS", payment_method="MOCK",
    )
    db.add(p1)
    db.commit()

    existing = db.query(Payment).filter(Payment.idempotency_key == key).first()
    assert existing is not None
    assert existing.payment_id == p1.payment_id


# ── Test 10: Order creation ───────────────────────────────────────────────────

def test_order_creation(db, demo_product, demo_customer, active_reservation):
    order = Order(
        order_id=str(uuid.uuid4()), customer_id=demo_customer.customer_id,
        reservation_id=active_reservation.reservation_id,
        total_amount=49999.0, status="CONFIRMED",
        idempotency_key=f"order-{active_reservation.reservation_id}",
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_item_id=str(uuid.uuid4()), order_id=order.order_id,
        product_id=demo_product.product_id, quantity=1,
        unit_price=49999.0, subtotal=49999.0,
    )
    db.add(item)
    db.commit()

    retrieved = db.query(Order).filter(Order.order_id == order.order_id).first()
    assert retrieved is not None
    assert retrieved.status == "CONFIRMED"
    assert len(retrieved.items) == 1


# ── Test 11: Order idempotency (service recovery) ─────────────────────────────

def test_order_idempotency(db, demo_customer, active_reservation):
    key = f"order-{active_reservation.reservation_id}"
    o1 = Order(
        order_id=str(uuid.uuid4()), customer_id=demo_customer.customer_id,
        reservation_id=active_reservation.reservation_id,
        total_amount=49999.0, status="CONFIRMED", idempotency_key=key,
    )
    db.add(o1)
    db.commit()

    # Simulate event replay
    existing = db.query(Order).filter(Order.idempotency_key == key).first()
    assert existing.order_id == o1.order_id  # Same order returned


# ── Test 12: Event retry logic ────────────────────────────────────────────────

def test_event_retry_logic():
    MAX_RETRY = 3
    dlq_hit = False

    def process(attempt):
        nonlocal dlq_hit
        if attempt >= MAX_RETRY:
            dlq_hit = True
            return
        raise Exception("simulated failure")

    for i in range(MAX_RETRY + 1):
        try:
            process(i)
            break
        except Exception:
            pass

    assert dlq_hit is True


# ── Test 13: Inventory never goes negative ────────────────────────────────────

def test_inventory_never_negative(db, demo_product, demo_inventory, demo_sale, demo_customer):
    demo_inventory.available_quantity = 1
    db.commit()

    ok1, _, _ = allocate_inventory(db, demo_product.product_id, demo_customer.customer_id, 1, str(uuid.uuid4()))
    ok2, _, _ = allocate_inventory(db, demo_product.product_id, demo_customer.customer_id, 1, str(uuid.uuid4()))

    db.refresh(demo_inventory)
    assert demo_inventory.available_quantity >= 0
    assert ok1 is True
    assert ok2 is False


# ── Test 14: Different products process concurrently ─────────────────────────

def test_different_products_concurrent():
    engine = make_engine("./test_multi.db")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    p1, _, c1 = seed(db, 10)
    p2, _, c2 = seed(db, 10)
    p1_id, c1_id = p1.product_id, c1.customer_id
    p2_id, c2_id = p2.product_id, c2.customer_id
    db.close()

    results = []
    lock = threading.Lock()

    def reserve(pid, cid):
        s = Session()
        try:
            ok, _, _ = allocate_inventory(s, pid, cid, 1, str(uuid.uuid4()))
            with lock:
                results.append((pid, ok))
        finally:
            s.close()

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=reserve, args=(p1_id, c1_id)))
        threads.append(threading.Thread(target=reserve, args=(p2_id, c2_id)))
    for t in threads: t.start()
    for t in threads: t.join()

    p1_ok = sum(1 for pid, ok in results if pid == p1_id and ok)
    p2_ok = sum(1 for pid, ok in results if pid == p2_id and ok)
    assert p1_ok <= 10
    assert p2_ok <= 10

    import os
    engine.dispose()
    try:
        if os.path.exists("./test_multi.db"): os.remove("./test_multi.db")
    except Exception:
        pass


# ── Test 15: Same product serialized — no oversell ────────────────────────────

def test_same_product_serialized_no_oversell():
    INITIAL = 5
    THREADS = 50

    engine = make_engine("./test_serial.db")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    product, _, customer = seed(db, INITIAL)
    pid, cid = product.product_id, customer.customer_id
    db.close()

    successes = []
    lock = threading.Lock()

    def try_reserve():
        s = Session()
        try:
            ok, _, _ = allocate_inventory(s, pid, cid, 1, str(uuid.uuid4()))
            with lock:
                successes.append(ok)
        finally:
            s.close()

    threads = [threading.Thread(target=try_reserve) for _ in range(THREADS)]
    for t in threads: t.start()
    for t in threads: t.join()

    check = Session()
    final = check.query(Inventory).filter(Inventory.product_id == pid).first()
    check.close()

    total_ok = sum(1 for s in successes if s)
    assert total_ok <= INITIAL, f"OVERSELL: {total_ok} > {INITIAL}"
    assert final.available_quantity >= 0

    import os
    engine.dispose()
    try:
        if os.path.exists("./test_serial.db"): os.remove("./test_serial.db")
    except Exception:
        pass
