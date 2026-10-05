"""
Admin API — full dashboard, management endpoints, demo controls.
Protected by JWT admin role OR legacy x-admin-key header.
"""
import uuid
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from app.core.database import get_db
from app.core.redis_client import get_async_redis
from app.core.config import get_settings
from app.services.product_service import invalidate_product_cache
from app.models.models import (
    Reservation, Order, Payment, Inventory, Product, Sale, Customer,
    Shipment, Notification, Coupon, Category, QueueRequest, AuditLog, OrderItem
)
from app.schemas.schemas import (
    AdminDashboardResponse, AdminSimulateRequest, AdminInventoryRow,
    AdminRestockRequest, SaleCreate, SaleUpdate, SaleResponse,
    CouponCreate, CouponResponse, AdminShipmentUpdateRequest,
    ProductCreate, CategoryResponse
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()
ADMIN_API_KEY = "admin-demo-key"


def require_admin(
    x_admin_key: str = Header(default=""),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> None:
    if x_admin_key == ADMIN_API_KEY:
        return
    if authorization.startswith("Bearer "):
        from app.services.auth_service import get_customer_from_token
        customer = get_customer_from_token(db, authorization[7:])
        if customer and customer.role == "ADMIN":
            return
    raise HTTPException(status_code=403, detail="Admin access required")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(db: Session = Depends(get_db), _=Depends(require_admin)):
    total_customers = db.query(Customer).count()
    total_products = db.query(Product).filter(Product.status == "ACTIVE").count()
    now = datetime.utcnow()
    active_sales = db.query(Sale).filter(
        Sale.status == "ACTIVE", Sale.start_time <= now, Sale.end_time >= now
    ).count()

    total_reservations = db.query(Reservation).count()
    active_reservations = db.query(Reservation).filter(
        Reservation.status.in_(["RESERVED", "PAYMENT_PENDING"])
    ).count()
    expired_reservations = db.query(Reservation).filter(
        Reservation.status == "EXPIRED"
    ).count()
    confirmed_reservations = db.query(Reservation).filter(
        Reservation.status == "CONFIRMED"
    ).count()

    payment_success = db.query(Payment).filter(Payment.status == "SUCCESS").count()
    payment_failure = db.query(Payment).filter(Payment.status == "FAILED").count()
    payment_timeout = db.query(Payment).filter(Payment.status == "TIMEOUT").count()
    orders_created = db.query(Order).count()

    total_revenue_row = db.query(func.sum(Order.total_amount)).filter(
        Order.status.in_(["CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"])
    ).scalar()
    total_revenue = float(total_revenue_row or 0)

    # Aggregate inventory across all products
    inv_rows = db.query(Inventory).all()
    current_inventory = sum(i.available_quantity for i in inv_rows)
    reserved_inventory = sum(i.reserved_quantity for i in inv_rows)
    sold_inventory = sum(i.sold_quantity for i in inv_rows)

    oversold = sum(abs(i.available_quantity) for i in inv_rows if i.available_quantity < 0)

    queue_len = 0
    avg_latency = 0.0
    total_queued = total_reservations
    try:
        redis = get_async_redis()
        queue_stats = await redis.hgetall("queue:stats")
        total_queued = int(queue_stats.get(b"total_queued", total_reservations) if queue_stats else total_reservations)
        active_sale = db.query(Sale).filter(Sale.status == "ACTIVE").first()
        if active_sale:
            queue_len = await redis.zcard(f"queue:waiting:{active_sale.sale_id}")
        avg_latency = float(await redis.get("metrics:avg_latency_ms") or 0)
    except Exception:
        pass

    return AdminDashboardResponse(
        total_customers=total_customers,
        total_products=total_products,
        active_sales=active_sales,
        total_requests=total_queued,
        successful_reservations=confirmed_reservations + active_reservations,
        rejected_requests=max(0, total_queued - (confirmed_reservations + active_reservations)),
        current_inventory=current_inventory,
        reserved_inventory=reserved_inventory,
        sold_inventory=sold_inventory,
        active_reservations=active_reservations,
        expired_reservations=expired_reservations,
        payment_success=payment_success,
        payment_failure=payment_failure,
        payment_timeout=payment_timeout,
        orders_created=orders_created,
        total_revenue=total_revenue,
        oversold_units=oversold,
        duplicate_requests=0,
        queue_length=queue_len,
        requests_per_second=0.0,
        average_latency_ms=avg_latency,
    )


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.get("/inventory", response_model=List[AdminInventoryRow])
def get_inventory(db: Session = Depends(get_db), _=Depends(require_admin)):
    rows = db.query(Inventory).all()
    result = []
    for inv in rows:
        product = db.query(Product).filter(Product.product_id == inv.product_id).first()
        if not product:
            continue
        total = inv.available_quantity + inv.reserved_quantity + inv.sold_quantity
        result.append(AdminInventoryRow(
            product_id=inv.product_id,
            product_name=product.name,
            sku=product.sku,
            available_quantity=inv.available_quantity,
            reserved_quantity=inv.reserved_quantity,
            sold_quantity=inv.sold_quantity,
            total_quantity=total,
            version=inv.version,
            updated_at=inv.updated_at,
        ))
    return result


@router.post("/inventory/restock")
def restock(request: AdminRestockRequest, db: Session = Depends(get_db), _=Depends(require_admin)):
    inv = db.query(Inventory).filter(Inventory.product_id == request.product_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory not found")
    inv.available_quantity += request.quantity
    inv.version += 1
    inv.updated_at = datetime.utcnow()
    db.commit()
    return {"message": f"Restocked {request.quantity} units", "new_available": inv.available_quantity}


# ── Sales ─────────────────────────────────────────────────────────────────────

@router.get("/sales", response_model=List[SaleResponse])
def list_sales(db: Session = Depends(get_db), _=Depends(require_admin)):
    sales = db.query(Sale).order_by(Sale.created_at.desc()).all()
    result = []
    for s in sales:
        product = db.query(Product).filter(Product.product_id == s.product_id).first()
        result.append(SaleResponse(
            sale_id=s.sale_id,
            product_id=s.product_id,
            sale_name=s.sale_name,
            start_time=s.start_time,
            end_time=s.end_time,
            sale_price=float(s.sale_price),
            sale_stock=s.sale_stock,
            status=s.status,
            product_name=product.name if product else None,
        ))
    return result


@router.post("/sales", response_model=SaleResponse, status_code=201)
def create_sale(request: SaleCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    product = db.query(Product).filter(Product.product_id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    sale = Sale(
        sale_id=str(uuid.uuid4()),
        product_id=request.product_id,
        sale_name=request.sale_name,
        start_time=request.start_time,
        end_time=request.end_time,
        sale_price=request.sale_price,
        sale_stock=request.sale_stock,
        status="SCHEDULED",
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return SaleResponse(
        sale_id=sale.sale_id, product_id=sale.product_id, sale_name=sale.sale_name,
        start_time=sale.start_time, end_time=sale.end_time, sale_price=float(sale.sale_price),
        sale_stock=sale.sale_stock, status=sale.status, product_name=product.name,
    )


@router.put("/sales/{sale_id}", response_model=SaleResponse)
async def update_sale(
    sale_id: str, request: SaleUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    for field, value in request.model_dump(exclude_none=True).items():
        setattr(sale, field, value)
    db.commit()
    db.refresh(sale)
    await invalidate_product_cache(sale.product_id)
    product = db.query(Product).filter(Product.product_id == sale.product_id).first()
    return SaleResponse(
        sale_id=sale.sale_id, product_id=sale.product_id, sale_name=sale.sale_name,
        start_time=sale.start_time, end_time=sale.end_time, sale_price=float(sale.sale_price),
        sale_stock=sale.sale_stock, status=sale.status, product_name=product.name if product else None,
    )


# ── Coupons ───────────────────────────────────────────────────────────────────

@router.get("/coupons", response_model=List[CouponResponse])
def list_coupons(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Coupon).order_by(Coupon.created_at.desc()).all()


@router.post("/coupons", response_model=CouponResponse, status_code=201)
def create_coupon(request: CouponCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(Coupon).filter(Coupon.code == request.code).first():
        raise HTTPException(status_code=409, detail="Coupon code already exists")
    coupon = Coupon(
        coupon_id=str(uuid.uuid4()),
        sale_id=request.sale_id,
        code=request.code.upper(),
        discount_type=request.discount_type,
        discount_value=request.discount_value,
        max_usage=request.max_usage,
        expires_at=request.expires_at,
        status="ACTIVE",
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}", status_code=204)
def deactivate_coupon(coupon_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    coupon.status = "INACTIVE"
    db.commit()


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders")
def admin_list_orders(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    if search:
        query = query.filter(Order.order_id.ilike(f"%{search}%"))
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    result = []
    for o in orders:
        customer = db.query(Customer).filter(Customer.customer_id == o.customer_id).first()
        items = db.query(OrderItem).filter(OrderItem.order_id == o.order_id).all()
        payment = db.query(Payment).filter(Payment.order_id == o.order_id).first()
        shipment = db.query(Shipment).filter(Shipment.order_id == o.order_id).first()
        result.append({
            "order_id": o.order_id,
            "customer_name": customer.name if customer else "Unknown",
            "customer_email": customer.email if customer else "",
            "total_amount": float(o.total_amount),
            "discount_amount": float(o.discount_amount) if o.discount_amount else 0,
            "coupon_code": o.coupon_code,
            "status": o.status,
            "item_count": len(items),
            "payment_status": payment.status if payment else None,
            "shipment_status": shipment.status if shipment else None,
            "created_at": o.created_at.isoformat(),
        })
    return result


@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: str,
    body: dict,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = body.get("status", order.status)
    order.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Order status updated", "status": order.status}


# ── Payments ──────────────────────────────────────────────────────────────────

@router.get("/payments")
def admin_list_payments(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.status == status)
    payments = query.order_by(Payment.created_at.desc()).limit(limit).all()
    result = []
    for p in payments:
        customer = db.query(Customer).filter(Customer.customer_id == p.customer_id).first()
        result.append({
            "payment_id": p.payment_id,
            "order_id": p.order_id,
            "customer_name": customer.name if customer else "Unknown",
            "customer_email": customer.email if customer else "",
            "amount": float(p.amount),
            "payment_method": p.payment_method,
            "status": p.status,
            "payment_reference": p.payment_reference,
            "created_at": p.created_at.isoformat(),
        })
    return result


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/customers")
def admin_list_customers(
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    from sqlalchemy import or_
    query = db.query(Customer)
    if search:
        query = query.filter(
            or_(Customer.name.ilike(f"%{search}%"), Customer.email.ilike(f"%{search}%"))
        )
    customers = query.order_by(Customer.created_at.desc()).limit(limit).all()
    result = []
    for c in customers:
        order_count = db.query(Order).filter(Order.customer_id == c.customer_id).count()
        result.append({
            "customer_id": c.customer_id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "role": c.role,
            "is_active": c.is_active,
            "order_count": order_count,
            "created_at": c.created_at.isoformat(),
        })
    return result


# ── Shipments ─────────────────────────────────────────────────────────────────

@router.get("/shipments")
def admin_list_shipments(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    query = db.query(Shipment)
    if status:
        query = query.filter(Shipment.status == status)
    shipments = query.order_by(Shipment.created_at.desc()).limit(limit).all()
    result = []
    for s in shipments:
        order = db.query(Order).filter(Order.order_id == s.order_id).first()
        customer = db.query(Customer).filter(Customer.customer_id == order.customer_id).first() if order else None
        result.append({
            "shipment_id": s.shipment_id,
            "order_id": s.order_id,
            "customer_name": customer.name if customer else "Unknown",
            "tracking_number": s.tracking_number,
            "carrier": s.carrier,
            "status": s.status,
            "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
            "shipped_at": s.shipped_at.isoformat() if s.shipped_at else None,
            "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
            "created_at": s.created_at.isoformat(),
        })
    return result


@router.put("/shipments/{shipment_id}")
def update_shipment(
    shipment_id: str,
    request: AdminShipmentUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment.status = request.status
    if request.carrier:
        shipment.carrier = request.carrier
    if request.status == "SHIPPED":
        shipment.shipped_at = datetime.utcnow()
    if request.status == "DELIVERED":
        shipment.delivered_at = datetime.utcnow()
        order = db.query(Order).filter(Order.order_id == shipment.order_id).first()
        if order:
            order.status = "DELIVERED"
    shipment.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Shipment updated", "status": shipment.status}


# ── Reservations ──────────────────────────────────────────────────────────────

@router.get("/reservations")
def admin_list_reservations(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    query = db.query(Reservation)
    if status:
        query = query.filter(Reservation.status == status)
    reservations = query.order_by(Reservation.created_at.desc()).limit(limit).all()
    result = []
    for r in reservations:
        customer = db.query(Customer).filter(Customer.customer_id == r.customer_id).first()
        product = db.query(Product).filter(Product.product_id == r.product_id).first()
        result.append({
            "reservation_id": r.reservation_id,
            "customer_name": customer.name if customer else "Unknown",
            "product_name": product.name if product else "Unknown",
            "quantity": r.quantity,
            "status": r.status,
            "expires_at": r.expires_at.isoformat(),
            "created_at": r.created_at.isoformat(),
        })
    return result


# ── Queue monitoring ──────────────────────────────────────────────────────────

@router.get("/queue")
async def admin_queue_stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    products = db.query(Product).filter(Product.status == "ACTIVE").all()
    result = []
    for product in products:
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()
        sale = db.query(Sale).filter(
            Sale.product_id == product.product_id, Sale.status == "ACTIVE"
        ).first()

        queue_len = 0
        waiting = 0
        admitted = 0
        completed = 0
        rejected = 0

        if sale:
            try:
                redis = get_async_redis()
                queue_len = await redis.zcard(f"queue:waiting:{sale.sale_id}")
                waiting = queue_len
            except Exception:
                pass

        # DB-based counts
        admitted = db.query(QueueRequest).filter(
            QueueRequest.product_id == product.product_id,
            QueueRequest.status == "ADMITTED",
        ).count()
        completed = db.query(QueueRequest).filter(
            QueueRequest.product_id == product.product_id,
            QueueRequest.status == "COMPLETED",
        ).count()
        rejected = db.query(QueueRequest).filter(
            QueueRequest.product_id == product.product_id,
            QueueRequest.status == "REJECTED",
        ).count()

        result.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "sale_active": sale is not None,
            "queue_length": queue_len,
            "waiting": waiting,
            "admitted": admitted,
            "completed": completed,
            "rejected": rejected,
            "current_inventory": inv.available_quantity if inv else 0,
            "reserved": inv.reserved_quantity if inv else 0,
            "sold": inv.sold_quantity if inv else 0,
        })
    return result


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
def admin_analytics(db: Session = Depends(get_db), _=Depends(require_admin)):
    # Orders over last 24 hours by hour
    now = datetime.utcnow()
    orders_by_hour = []
    for h in range(23, -1, -1):
        start = now - timedelta(hours=h + 1)
        end = now - timedelta(hours=h)
        count = db.query(Order).filter(Order.created_at >= start, Order.created_at < end).count()
        revenue_row = db.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= start, Order.created_at < end,
            Order.status.in_(["CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"])
        ).scalar()
        orders_by_hour.append({
            "hour": end.strftime("%H:00"),
            "orders": count,
            "revenue": float(revenue_row or 0),
        })

    # Payment breakdown
    payment_stats = {
        "SUCCESS": db.query(Payment).filter(Payment.status == "SUCCESS").count(),
        "FAILED": db.query(Payment).filter(Payment.status == "FAILED").count(),
        "TIMEOUT": db.query(Payment).filter(Payment.status == "TIMEOUT").count(),
        "UNKNOWN": db.query(Payment).filter(Payment.status == "UNKNOWN").count(),
    }

    # Reservation breakdown
    reservation_stats = {
        "RESERVED": db.query(Reservation).filter(Reservation.status == "RESERVED").count(),
        "CONFIRMED": db.query(Reservation).filter(Reservation.status == "CONFIRMED").count(),
        "EXPIRED": db.query(Reservation).filter(Reservation.status == "EXPIRED").count(),
        "PAYMENT_FAILED": db.query(Reservation).filter(Reservation.status == "PAYMENT_FAILED").count(),
    }

    # Top products by orders
    top_products = []
    products = db.query(Product).filter(Product.status == "ACTIVE").all()
    for p in products:
        from sqlalchemy import text
        count = db.query(OrderItem).filter(OrderItem.product_id == p.product_id).count()
        inv = db.query(Inventory).filter(Inventory.product_id == p.product_id).first()
        top_products.append({
            "product_id": p.product_id,
            "name": p.name,
            "orders": count,
            "sold": inv.sold_quantity if inv else 0,
        })
    top_products.sort(key=lambda x: x["orders"], reverse=True)

    return {
        "orders_by_hour": orders_by_hour,
        "payment_stats": payment_stats,
        "reservation_stats": reservation_stats,
        "top_products": top_products[:10],
    }


# ── Simulate / Demo controls ──────────────────────────────────────────────────

@router.post("/simulate")
async def simulate_action(
    request: AdminSimulateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    action = request.action

    if action == "RESET_INVENTORY":
        product = db.query(Product).filter(Product.sku == settings.demo_product_sku).first()
        if not product:
            raise HTTPException(status_code=404, detail="Demo product not found")
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()
        if inv:
            inv.available_quantity = settings.demo_initial_inventory
            inv.reserved_quantity = 0
            inv.sold_quantity = 0
            inv.version += 1
            inv.updated_at = datetime.utcnow()
            db.commit()
            await invalidate_product_cache(product.product_id)
        return {"message": f"Inventory reset to {settings.demo_initial_inventory}"}

    elif action == "SET_INVENTORY":
        if request.quantity is None:
            raise HTTPException(status_code=400, detail="quantity required")
        product_id = request.product_id
        if not product_id:
            p = db.query(Product).filter(Product.sku == settings.demo_product_sku).first()
            product_id = p.product_id if p else None
        if not product_id:
            raise HTTPException(status_code=404, detail="Product not found")
        inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
        if inv:
            inv.available_quantity = request.quantity
            inv.version += 1
            inv.updated_at = datetime.utcnow()
            db.commit()
            await invalidate_product_cache(product_id)
        return {"message": f"Inventory set to {request.quantity}"}

    elif action == "START_SALE":
        product_id = request.product_id
        if not product_id:
            p = db.query(Product).filter(Product.sku == settings.demo_product_sku).first()
            product_id = p.product_id if p else None
        if not product_id:
            raise HTTPException(status_code=404, detail="Product not found")
        sale = db.query(Sale).filter(Sale.product_id == product_id).first()
        if sale:
            sale.status = "ACTIVE"
            sale.start_time = datetime.utcnow()
            sale.end_time = datetime.utcnow() + timedelta(hours=2)
            db.commit()
            await invalidate_product_cache(product_id)
        return {"message": "Sale started"}

    elif action == "STOP_SALE":
        product_id = request.product_id
        if not product_id:
            p = db.query(Product).filter(Product.sku == settings.demo_product_sku).first()
            product_id = p.product_id if p else None
        if not product_id:
            raise HTTPException(status_code=404, detail="Product not found")
        sale = db.query(Sale).filter(Sale.product_id == product_id).first()
        if sale:
            sale.status = "ENDED"
            sale.end_time = datetime.utcnow()
            db.commit()
            await invalidate_product_cache(product_id)
        return {"message": "Sale stopped"}

    elif action == "EXPIRE_RESERVATIONS":
        reservations = db.query(Reservation).filter(
            Reservation.status.in_(["RESERVED", "PAYMENT_PENDING"])
        ).all()
        for r in reservations:
            r.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        return {"message": f"Marked {len(reservations)} reservations as expiring"}

    elif action == "CLEAR_QUEUE":
        try:
            redis = get_async_redis()
            sale = db.query(Sale).filter(Sale.status == "ACTIVE").first()
            if sale:
                await redis.delete(f"queue:waiting:{sale.sale_id}")
            await redis.delete("queue:stats")
        except Exception:
            pass
        return {"message": "Queue cleared"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


# ── Demo customer ─────────────────────────────────────────────────────────────

@router.post("/customers/demo", status_code=201)
def create_demo_customer(db: Session = Depends(get_db)):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    customer_id = str(uuid.uuid4())
    email = f"user_{customer_id[:8]}@salestorm.io"
    customer = Customer(
        customer_id=customer_id,
        name=f"Demo User {customer_id[:8]}",
        email=email,
        password_hash=pwd_context.hash("demo1234"),
        role="CUSTOMER",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"customer_id": customer.customer_id, "email": customer.email}
