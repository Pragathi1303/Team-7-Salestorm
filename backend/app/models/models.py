import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, DateTime, ForeignKey,
    UniqueConstraint, Index, Boolean, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="CUSTOMER")  # CUSTOMER | ADMIN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    carts: Mapped[list["Cart"]] = relationship(back_populates="customer")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="customer", foreign_keys="Notification.customer_id")
    addresses: Mapped[list["Address"]] = relationship(back_populates="customer")


class Address(Base):
    __tablename__ = "addresses"

    address_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    line1: Mapped[str] = mapped_column(String(500), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="addresses")


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.category_id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    brand: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category | None"] = relationship(back_populates="products")
    inventory: Mapped["Inventory | None"] = relationship(back_populates="product", uselist=False)
    sales: Mapped[list["Sale"]] = relationship(back_populates="product")
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")


class Sale(Base):
    __tablename__ = "sales"

    sale_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"), nullable=False)
    sale_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sale_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    sale_stock: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED")  # SCHEDULED|ACTIVE|PAUSED|ENDED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"] = relationship(back_populates="sales")
    coupons: Mapped[list["Coupon"]] = relationship(back_populates="sale")


class Coupon(Base):
    __tablename__ = "coupons"

    coupon_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    sale_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sales.sale_id"))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PERCENTAGE | FIXED
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_usage: Mapped[int] = mapped_column(Integer, default=100)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE | INACTIVE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sale: Mapped["Sale | None"] = relationship(back_populates="coupons")


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"), unique=True, nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sold_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"] = relationship(back_populates="inventory")

    __table_args__ = (
        Index("ix_inventory_product_id", "product_id"),
    )


class Cart(Base):
    __tablename__ = "carts"

    cart_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="carts")
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    cart_item_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    cart_id: Mapped[str] = mapped_column(String(36), ForeignKey("carts.cart_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    cart: Mapped["Cart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="cart_items")

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )


class Reservation(Base):
    __tablename__ = "reservations"

    reservation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), default="RESERVED")
    # RESERVED → PAYMENT_PENDING → CONFIRMED → SOLD
    # RESERVED → PAYMENT_FAILED → RELEASED
    # RESERVED → EXPIRED
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="reservations")
    orders: Mapped[list["Order"]] = relationship(back_populates="reservation")

    __table_args__ = (
        Index("ix_reservation_customer_product", "customer_id", "product_id"),
        Index("ix_reservation_status", "status"),
        Index("ix_reservation_expires_at", "expires_at"),
    )


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    reservation_id: Mapped[str] = mapped_column(String(36), ForeignKey("reservations.reservation_id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    coupon_code: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")
    # CONFIRMED → PROCESSING → SHIPPED → OUT_FOR_DELIVERY → DELIVERED | CANCELLED | REFUNDED
    shipping_address: Mapped[str | None] = mapped_column(Text)  # JSON string
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    reservation: Mapped["Reservation"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="order")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="order", foreign_keys="Notification.order_id")

    __table_args__ = (
        Index("ix_order_customer_id", "customer_id"),
        Index("ix_order_status", "status"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.order_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orders.order_id"))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_reference: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, default=gen_uuid)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="INITIATED")
    # INITIATED → PROCESSING → SUCCESS | FAILED | TIMEOUT | UNKNOWN | REFUNDED
    payment_method: Mapped[str] = mapped_column(String(100), default="CARD")
    # CARD | UPI | NET_BANKING | WALLET | MOCK
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order: Mapped["Order | None"] = relationship(back_populates="payments")

    __table_args__ = (
        Index("ix_payment_customer_id", "customer_id"),
        Index("ix_payment_status", "status"),
    )


class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.order_id"), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, default=gen_uuid)
    carrier: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="CREATED")
    # CREATED → PACKED → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="shipments")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orders.order_id"))
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="SENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="notifications", foreign_keys=[customer_id])
    order: Mapped["Order | None"] = relationship(back_populates="notifications", foreign_keys=[order_id])

    __table_args__ = (
        Index("ix_notification_customer_id", "customer_id"),
        Index("ix_notification_is_read", "is_read"),
    )


class QueueRequest(Base):
    __tablename__ = "queue_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    queue_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"), nullable=False)
    sale_id: Mapped[str] = mapped_column(String(36), ForeignKey("sales.sale_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="WAITING")
    # WAITING | ADMITTED | PROCESSING | COMPLETED | REJECTED | EXPIRED
    position: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_queue_request_product_id", "product_id"),
        Index("ix_queue_request_status", "status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )
