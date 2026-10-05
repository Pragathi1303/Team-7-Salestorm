"""
Shipments API.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_customer
from app.models.models import Shipment, Order
from app.schemas.schemas import ShipmentResponse

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: str,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Verify ownership
    order = db.query(Order).filter(Order.order_id == shipment.order_id).first()
    if not order or order.customer_id != customer.customer_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return shipment


@router.get("/by-order/{order_id}", response_model=list[ShipmentResponse])
def get_shipments_by_order(
    order_id: str,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(
        Order.order_id == order_id,
        Order.customer_id == customer.customer_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return db.query(Shipment).filter(Shipment.order_id == order_id).all()
