"""
Initialize database tables and seed demo data.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.core.database import engine, Base, SessionLocal
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.models import Category, Product, Inventory, Sale, Customer, Coupon

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def create_tables():
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")


def seed_demo_data(db: Session):
    if db.query(Product).filter(Product.sku == settings.demo_product_sku).first():
        logger.info("demo_data_already_seeded")
        return

    # ── Categories ────────────────────────────────────────────────────────────
    cat_electronics = Category(
        category_id=str(uuid.uuid4()),
        category_name="Electronics",
        description="Smartphones, TVs, Laptops and more",
        image_url="https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400",
        is_active=True,
    )
    cat_fashion = Category(
        category_id=str(uuid.uuid4()),
        category_name="Fashion",
        description="Clothing, shoes and accessories",
        image_url="https://images.unsplash.com/photo-1445205170230-053b83016050?w=400",
        is_active=True,
    )
    cat_appliances = Category(
        category_id=str(uuid.uuid4()),
        category_name="Appliances",
        description="Home and kitchen appliances",
        image_url="https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400",
        is_active=True,
    )
    db.add_all([cat_electronics, cat_fashion, cat_appliances])
    db.flush()

    # ── Products ──────────────────────────────────────────────────────────────
    now = datetime.utcnow()

    products_data = [
        {
            "sku": settings.demo_product_sku,
            "name": 'Ultra HD Smart TV 55"',
            "description": "4K Ultra HD Smart TV with HDR, Dolby Vision and built-in streaming apps. Experience cinema-quality visuals at home.",
            "price": 79999.00,
            "category_id": cat_electronics.category_id,
            "image_url": "https://images.unsplash.com/photo-1593359677879-a4bb92f829e1?w=600",
            "brand": "SamsVision",
            "stock": settings.demo_initial_inventory,
            "sale_price": 49999.00,
            "is_flash": True,
        },
        {
            "sku": "P002",
            "name": "iPhone 15 Pro Max",
            "description": "Latest flagship smartphone with A17 Pro chip, 48MP camera system and titanium design.",
            "price": 134900.00,
            "category_id": cat_electronics.category_id,
            "image_url": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600",
            "brand": "Apple",
            "stock": 50,
            "sale_price": 109900.00,
            "is_flash": True,
        },
        {
            "sku": "P003",
            "name": "Sony WH-1000XM5 Headphones",
            "description": "Industry-leading noise cancelling headphones with 30-hour battery life and crystal clear hands-free calling.",
            "price": 29990.00,
            "category_id": cat_electronics.category_id,
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600",
            "brand": "Sony",
            "stock": 200,
            "sale_price": None,
            "is_flash": False,
        },
        {
            "sku": "P004",
            "name": "Nike Air Max 270",
            "description": "Iconic Air Max cushioning with a large Air unit for all-day comfort. Available in multiple colorways.",
            "price": 12995.00,
            "category_id": cat_fashion.category_id,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600",
            "brand": "Nike",
            "stock": 300,
            "sale_price": 8995.00,
            "is_flash": False,
        },
        {
            "sku": "P005",
            "name": "Dyson V15 Detect Vacuum",
            "description": "Powerful cordless vacuum with laser dust detection and HEPA filtration. Up to 60 minutes run time.",
            "price": 52900.00,
            "category_id": cat_appliances.category_id,
            "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600",
            "brand": "Dyson",
            "stock": 75,
            "sale_price": 39900.00,
            "is_flash": True,
        },
    ]

    created_products = []
    for pd in products_data:
        product = Product(
            product_id=str(uuid.uuid4()),
            category_id=pd["category_id"],
            name=pd["name"],
            description=pd["description"],
            price=pd["price"],
            sku=pd["sku"],
            image_url=pd["image_url"],
            brand=pd["brand"],
            status="ACTIVE",
        )
        db.add(product)
        db.flush()

        inventory = Inventory(
            inventory_id=str(uuid.uuid4()),
            product_id=product.product_id,
            available_quantity=pd["stock"],
            reserved_quantity=0,
            sold_quantity=0,
            version=1,
        )
        db.add(inventory)

        if pd["is_flash"] and pd["sale_price"]:
            sale = Sale(
                sale_id=str(uuid.uuid4()),
                product_id=product.product_id,
                sale_name=f"SALESTORM Flash Sale — {pd['name'][:30]}",
                start_time=now - timedelta(minutes=5),
                end_time=now + timedelta(hours=2),
                sale_price=pd["sale_price"],
                sale_stock=pd["stock"],
                status="ACTIVE",
            )
            db.add(sale)

        created_products.append(product)

    # ── Coupons ───────────────────────────────────────────────────────────────
    coupons = [
        Coupon(
            coupon_id=str(uuid.uuid4()),
            code="STORM10",
            discount_type="PERCENTAGE",
            discount_value=10.0,
            max_usage=500,
            expires_at=now + timedelta(days=30),
            status="ACTIVE",
        ),
        Coupon(
            coupon_id=str(uuid.uuid4()),
            code="FLAT500",
            discount_type="FIXED",
            discount_value=500.0,
            max_usage=200,
            expires_at=now + timedelta(days=30),
            status="ACTIVE",
        ),
        Coupon(
            coupon_id=str(uuid.uuid4()),
            code="WELCOME20",
            discount_type="PERCENTAGE",
            discount_value=20.0,
            max_usage=100,
            expires_at=now + timedelta(days=7),
            status="ACTIVE",
        ),
    ]
    db.add_all(coupons)

    # ── Users ─────────────────────────────────────────────────────────────────
    demo_customer = Customer(
        customer_id=str(uuid.uuid4()),
        name="Demo User",
        email="demo@salestorm.io",
        phone="+91-9876543210",
        password_hash=pwd_context.hash("demo1234"),
        role="CUSTOMER",
        is_active=True,
    )
    admin_user = Customer(
        customer_id=str(uuid.uuid4()),
        name="Admin",
        email="admin@salestorm.io",
        phone="+91-9000000000",
        password_hash=pwd_context.hash("admin1234"),
        role="ADMIN",
        is_active=True,
    )
    db.add_all([demo_customer, admin_user])

    db.commit()
    logger.info(
        "demo_data_seeded",
        products=len(products_data),
        coupons=len(coupons),
    )


def init_db():
    create_tables()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
