from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.payment_service import process_payment, get_payment
from app.schemas.schemas import PaymentRequest, PaymentResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def make_payment(request: PaymentRequest, db: Session = Depends(get_db)):
    success, message, payment, order = await process_payment(
        db=db,
        reservation_id=request.reservation_id,
        customer_id=request.customer_id,
        amount=request.amount,
        payment_method=request.payment_method,
        idempotency_key=request.idempotency_key,
        simulate_outcome=request.simulate_outcome,
        coupon_code=request.coupon_code,
        shipping_address=request.shipping_address,
    )

    if payment is None:
        status_map = {
            "reservation_not_found": 404,
            "unauthorized": 403,
            "reservation_expired": 400,
        }
        code = 400
        for key, val in status_map.items():
            if key in message:
                code = val
                break
        raise HTTPException(status_code=code, detail=message)

    return PaymentResponse(
        payment_id=payment.payment_id,
        order_id=payment.order_id,
        status=payment.status,
        payment_reference=payment.payment_reference,
        amount=float(payment.amount),
        payment_method=payment.payment_method,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_detail(payment_id: str, db: Session = Depends(get_db)):
    payment = get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(
        payment_id=payment.payment_id,
        order_id=payment.order_id,
        status=payment.status,
        payment_reference=payment.payment_reference,
        amount=float(payment.amount),
        payment_method=payment.payment_method,
        created_at=payment.created_at,
    )
