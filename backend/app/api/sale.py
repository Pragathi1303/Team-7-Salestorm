from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.virtual_queue import join_queue, get_queue_status
from app.schemas.schemas import JoinQueueRequest, QueueStatusResponse

router = APIRouter(prefix="/api/sale", tags=["sale", "queue"])


@router.post("/join", response_model=QueueStatusResponse)
async def join_sale_queue(
    request: JoinQueueRequest,
    db: Session = Depends(get_db),
):
    """
    Step 1 of the purchase flow.
    Validates the request and adds the customer to the virtual queue.
    Returns a queue token and position.
    """
    from app.models.models import Sale, Product
    from datetime import datetime

    # Validate product
    product = db.query(Product).filter(Product.product_id == request.product_id).first()
    if not product or product.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    # Validate active sale
    now = datetime.utcnow()
    sale = (
        db.query(Sale)
        .filter(
            Sale.sale_id == request.sale_id,
            Sale.status == "ACTIVE",
            Sale.start_time <= now,
            Sale.end_time >= now,
        )
        .first()
    )
    if not sale:
        raise HTTPException(status_code=400, detail="Sale is not active")

    result = await join_queue(
        sale_id=request.sale_id,
        customer_id=request.customer_id,
        product_id=request.product_id,
        quantity=request.quantity,
        idempotency_key=request.idempotency_key,
    )

    return QueueStatusResponse(
        queue_token=result["queue_token"],
        position=result["position"],
        queue_length=result.get("queue_length", result["position"]),
        status=result["status"],
        estimated_wait_seconds=result["position"] * 0.1,
        duplicate=result.get("duplicate", False),
    )


@router.get("/queue/{queue_token}", response_model=QueueStatusResponse)
async def get_queue_position(queue_token: str):
    """Poll queue status by token."""
    status = await get_queue_status(queue_token)
    if not status:
        raise HTTPException(status_code=404, detail="Queue token not found or expired")

    return QueueStatusResponse(
        queue_token=queue_token,
        position=status["position"],
        queue_length=status["queue_length"],
        status=status["status"],
        estimated_wait_seconds=status["estimated_wait_seconds"],
    )
