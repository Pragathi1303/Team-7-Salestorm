from datetime import datetime
from typing import Optional, Union, List
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: str
    name: str
    email: str
    role: str


# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)


class CustomerResponse(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Address ───────────────────────────────────────────────────────────────────

class AddressCreate(BaseModel):
    full_name: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"
    is_default: bool = False


class AddressResponse(BaseModel):
    address_id: str
    full_name: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str
    is_default: bool

    model_config = {"from_attributes": True}


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryResponse(BaseModel):
    category_id: str
    category_name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    sku: str
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    initial_stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    status: Optional[str] = None
    category_id: Optional[str] = None


class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: Optional[str] = None
    price: float
    sku: str
    status: str
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductWithSaleResponse(ProductResponse):
    sale_price: Optional[float] = None
    sale_id: Optional[str] = None
    sale_end_time: Optional[Union[datetime, str]] = None
    sale_name: Optional[str] = None
    available_quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    sold_quantity: Optional[int] = None
    category_name: Optional[str] = None


# ── Sale ──────────────────────────────────────────────────────────────────────

class SaleCreate(BaseModel):
    product_id: str
    sale_name: str
    start_time: datetime
    end_time: datetime
    sale_price: float = Field(..., gt=0)
    sale_stock: Optional[int] = None


class SaleUpdate(BaseModel):
    sale_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sale_price: Optional[float] = None
    sale_stock: Optional[int] = None
    status: Optional[str] = None


class SaleResponse(BaseModel):
    sale_id: str
    product_id: str
    sale_name: str
    start_time: datetime
    end_time: datetime
    sale_price: float
    sale_stock: Optional[int] = None
    status: str
    product_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Coupon ────────────────────────────────────────────────────────────────────

class CouponCreate(BaseModel):
    sale_id: Optional[str] = None
    code: str
    discount_type: str  # PERCENTAGE | FIXED
    discount_value: float = Field(..., gt=0)
    max_usage: int = 100
    expires_at: Optional[datetime] = None


class CouponValidateRequest(BaseModel):
    code: str
    amount: float


class CouponResponse(BaseModel):
    coupon_id: str
    code: str
    discount_type: str
    discount_value: float
    max_usage: int
    used_count: int
    expires_at: Optional[datetime] = None
    status: str

    model_config = {"from_attributes": True}


class CouponValidateResponse(BaseModel):
    valid: bool
    discount_amount: float
    final_amount: float
    message: str


# ── Queue ─────────────────────────────────────────────────────────────────────

class JoinQueueRequest(BaseModel):
    sale_id: str
    customer_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1, le=10)
    idempotency_key: str = Field(..., min_length=1, max_length=255)


class QueueStatusResponse(BaseModel):
    queue_token: str
    position: int
    queue_length: int
    status: str
    estimated_wait_seconds: float
    duplicate: bool = False


# ── Cart ──────────────────────────────────────────────────────────────────────

class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=10)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=10)


class CartItemResponse(BaseModel):
    cart_item_id: str
    product_id: str
    product_name: Optional[str] = None
    product_image: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    cart_id: str
    customer_id: str
    items: List[CartItemResponse] = []
    subtotal: float
    item_count: int

    model_config = {"from_attributes": True}


# ── Reservation ───────────────────────────────────────────────────────────────

class ReservationRequest(BaseModel):
    customer_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1, le=10)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    queue_token: Optional[str] = None


class ReservationResponse(BaseModel):
    reservation_id: str
    customer_id: str
    product_id: str
    quantity: int
    status: str
    expires_at: datetime
    idempotency_key: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Checkout ──────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    reservation_id: str
    customer_id: str
    coupon_code: Optional[str] = None
    shipping_address: Optional[dict] = None


class CheckoutResponse(BaseModel):
    reservation_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    discount_amount: float
    total_amount: float
    coupon_code: Optional[str] = None
    expires_at: datetime
    status: str


# ── Payment ───────────────────────────────────────────────────────────────────

class PaymentRequest(BaseModel):
    reservation_id: str
    customer_id: str
    amount: float = Field(..., gt=0)
    payment_method: str = Field(default="CARD")
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    coupon_code: Optional[str] = None
    shipping_address: Optional[dict] = None
    simulate_outcome: Optional[str] = Field(
        default=None,
        description="MOCK only: SUCCESS | FAILED | TIMEOUT"
    )


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: Optional[str] = None
    status: str
    payment_reference: str
    amount: float
    payment_method: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Order ─────────────────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    order_item_id: str
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class ShipmentResponse(BaseModel):
    shipment_id: str
    tracking_number: str
    carrier: Optional[str] = None
    status: str
    estimated_delivery: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    reservation_id: str
    total_amount: float
    discount_amount: float
    coupon_code: Optional[str] = None
    status: str
    shipping_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    shipments: List[ShipmentResponse] = []
    payments: List[PaymentResponse] = []

    model_config = {"from_attributes": True}


class OrderCancelRequest(BaseModel):
    reason: Optional[str] = None


# ── Notification ──────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    notification_id: str
    notification_type: str
    title: str
    message: str
    is_read: bool
    order_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminDashboardResponse(BaseModel):
    total_customers: int
    total_products: int
    active_sales: int
    total_requests: int
    successful_reservations: int
    rejected_requests: int
    current_inventory: int
    reserved_inventory: int
    sold_inventory: int
    active_reservations: int
    expired_reservations: int
    payment_success: int
    payment_failure: int
    payment_timeout: int
    orders_created: int
    total_revenue: float
    oversold_units: int
    duplicate_requests: int
    queue_length: int
    requests_per_second: float
    average_latency_ms: float


class AdminInventoryRow(BaseModel):
    product_id: str
    product_name: str
    sku: str
    available_quantity: int
    reserved_quantity: int
    sold_quantity: int
    total_quantity: int
    version: int
    updated_at: datetime


class AdminRestockRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class AdminSetInventoryRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=0)


class AdminSaleControlRequest(BaseModel):
    product_id: str
    action: str


class AdminSimulateRequest(BaseModel):
    action: str
    product_id: Optional[str] = None
    quantity: Optional[int] = None


class AdminShipmentUpdateRequest(BaseModel):
    status: str
    carrier: Optional[str] = None


class AdminQueueStats(BaseModel):
    product_id: str
    product_name: str
    queue_length: int
    waiting: int
    admitted: int
    completed: int
    rejected: int
    current_inventory: int
    reserved: int
    sold: int


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
