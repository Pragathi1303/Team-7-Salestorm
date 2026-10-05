from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.virtual_queue import get_queue_status, update_token_status
from app.services.reservation_service import create_reservation, get_reservation, cancel_reservation
from app.schemas.schemas import ReservationRequest, ReservationResponse

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


@router.post("", response_model=ReservationResponse, status_code=201)
async def make_reservation(
    request: ReservationRequest,
    db: Session = Depends(get_db),
):
    """
    Step 2 of the purchase flow.
    Allocates inventory and creates a reservation.
    Idempotent: same idempotency_key returns the same reservation.

    If queue_token is provided, validates the token is ADMITTED.
    Direct API calls (no queue_token) are allowed for testing/load tests.
    """
    # If queue token provided, validate it's admitted
    if request.queue_token:
        token_status = await get_queue_status(request.queue_token)
        if not token_status:
            raise HTTPException(status_code=400, detail="Invalid or expired queue token")
        if token_status["status"] not in ("ADMITTED", "WAITING"):
            raise HTTPException(
                status_code=400,
                detail=f"Queue token status is {token_status['status']}, not admitted"
            )

    success, message, reservation = await create_reservation(
        db=db,
        customer_id=request.customer_id,
        product_id=request.product_id,
        quantity=request.quantity,
        idempotency_key=request.idempotency_key,
    )

    if not success:
        status_map = {
            "out_of_stock": 409,
            "no_active_sale": 400,
            "product_not_found_or_inactive": 404,
        }
        status_code = status_map.get(message, 400)
        raise HTTPException(status_code=status_code, detail=message)

    # Update queue token status
    if request.queue_token:
        await update_token_status(
            request.queue_token,
            "COMPLETED",
            reservation_id=reservation.reservation_id,
        )

    return ReservationResponse(
        reservation_id=reservation.reservation_id,
        customer_id=reservation.customer_id,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at,
        idempotency_key=reservation.idempotency_key,
        created_at=reservation.created_at,
    )


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation_detail(reservation_id: str, db: Session = Depends(get_db)):
    reservation = get_reservation(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


@router.delete("/{reservation_id}", status_code=204)
async def cancel_reservation_endpoint(
    reservation_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
):
    success = await cancel_reservation(db, reservation_id, customer_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel reservation")
