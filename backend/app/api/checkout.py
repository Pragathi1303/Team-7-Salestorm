"""
Checkout API — validates reservation, applies coupon, returns checkout summary.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.models.models import Reservation, Product, Sale, Coupon
from app.schemas.schemas import CheckoutRequest, CheckoutResponse, CouponValidateRequest, CouponValidateResponse

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


def _calculate_discount(coupon: Coupon, amount: float) -> float:
    if coupon.discount_type == "PERCENTAGE":
        return round(amount * float(coupon.discount_value) / 100, 2)
    else:  # FIXED
        return min(float(coupon.discount_value), amount)


@router.post("", response_model=CheckoutResponse)
def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.reservation_id == request.reservation_id,
            Reservation.customer_id == request.customer_id,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status not in ("RESERVED", "PAYMENT_PENDING"):
        raise HTTPException(status_code=400, detail=f"Reservation status is {reservation.status}")
    if reservation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reservation has expired")

    product = db.query(Product).filter(Product.product_id == reservation.product_id).first()
    sale = (
        db.query(Sale)
        .filter(Sale.product_id == reservation.product_id, Sale.status == "ACTIVE")
        .first()
    )
    unit_price = float(sale.sale_price) if sale else float(product.price)
    subtotal = unit_price * reservation.quantity

    # Apply coupon if provided
    discount_amount = 0.0
    coupon_code = None
    if request.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == request.coupon_code,
            Coupon.status == "ACTIVE",
        ).first()
        if coupon:
            now = datetime.utcnow()
            if (not coupon.expires_at or coupon.expires_at > now) and coupon.used_count < coupon.max_usage:
                discount_amount = _calculate_discount(coupon, subtotal)
                coupon_code = coupon.code

    total = max(0.0, subtotal - discount_amount)

    return CheckoutResponse(
        reservation_id=reservation.reservation_id,
        product_name=product.name,
        quantity=reservation.quantity,
        unit_price=unit_price,
        subtotal=subtotal,
        discount_amount=discount_amount,
        total_amount=total,
        coupon_code=coupon_code,
        expires_at=reservation.expires_at,
        status=reservation.status,
    )


@router.post("/validate-coupon", response_model=CouponValidateResponse)
def validate_coupon(request: CouponValidateRequest, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(
        Coupon.code == request.code,
        Coupon.status == "ACTIVE",
    ).first()

    if not coupon:
        return CouponValidateResponse(valid=False, discount_amount=0, final_amount=request.amount, message="Coupon not found")

    now = datetime.utcnow()
    if coupon.expires_at and coupon.expires_at < now:
        return CouponValidateResponse(valid=False, discount_amount=0, final_amount=request.amount, message="Coupon expired")

    if coupon.used_count >= coupon.max_usage:
        return CouponValidateResponse(valid=False, discount_amount=0, final_amount=request.amount, message="Coupon usage limit reached")

    discount = _calculate_discount(coupon, request.amount)
    final = max(0.0, request.amount - discount)
    return CouponValidateResponse(valid=True, discount_amount=discount, final_amount=final, message="Coupon applied")
