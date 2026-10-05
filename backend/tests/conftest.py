import os
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Set env vars before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./conftest_test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test_secret")
os.environ.setdefault("RESERVATION_EXPIRY_SECONDS", "30")
os.environ.setdefault("DEMO_PRODUCT_SKU", "P001")
os.environ.setdefault("DEMO_INITIAL_INVENTORY", "100")

from app.core.database import Base
from app.models.models import (
    Customer, Product, Category, Inventory, Sale, Reservation
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_DB_URL = "sqlite:///./conftest_test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def demo_category(db):
    cat = Category(
        category_id=str(uuid.uuid4()),
        category_name="Electronics",
        description="Test category",
    )
    db.add(cat)
    db.commit()
    return cat


@pytest.fixture
def demo_product(db, demo_category):
    product = Product(
        product_id=str(uuid.uuid4()),
        category_id=demo_category.category_id,
        name="Test TV",
        description="Test product",
        price=79999.00,
        sku=f"P001-{uuid.uuid4().hex[:4]}",
        status="ACTIVE",
    )
    db.add(product)
    db.commit()
    return product


@pytest.fixture
def demo_inventory(db, demo_product):
    inv = Inventory(
        inventory_id=str(uuid.uuid4()),
        product_id=demo_product.product_id,
        available_quantity=100,
        reserved_quantity=0,
        sold_quantity=0,
        version=1,
    )
    db.add(inv)
    db.commit()
    return inv


@pytest.fixture
def demo_sale(db, demo_product):
    now = datetime.utcnow()
    sale = Sale(
        sale_id=str(uuid.uuid4()),
        product_id=demo_product.product_id,
        sale_name="Test Flash Sale",
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(hours=2),
        sale_price=49999.00,
        status="ACTIVE",
    )
    db.add(sale)
    db.commit()
    return sale


@pytest.fixture
def demo_customer(db):
    customer = Customer(
        customer_id=str(uuid.uuid4()),
        name="Test User",
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=pwd.hash("test1234"),
    )
    db.add(customer)
    db.commit()
    return customer


@pytest.fixture
def active_reservation(db, demo_customer, demo_product, demo_inventory, demo_sale):
    """A valid non-expired reservation with inventory already decremented."""
    reservation = Reservation(
        reservation_id=str(uuid.uuid4()),
        customer_id=demo_customer.customer_id,
        product_id=demo_product.product_id,
        quantity=1,
        status="RESERVED",
        idempotency_key=str(uuid.uuid4()),
        expires_at=datetime.utcnow() + timedelta(seconds=30),
    )
    db.add(reservation)
    demo_inventory.available_quantity -= 1
    demo_inventory.reserved_quantity += 1
    db.commit()
    return reservation
