"""
Orders API — list, detail, cancel.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_customer
from app.services.order_service import get_order_with_items
from app.models.models import Order, OrderItem, Payment, Shipment, Product
from app.schemas.schemas import OrderResponse, OrderItemResponse, PaymentResponse, ShipmentResponse, OrderCancelRequest

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _build_order_response(order: Order, db: Session) -> OrderResponse:
    items = []
    for item in order.items:
        product = db.query(Product).filter(Product.product_id == item.product_id).first()
        items.append(OrderItemResponse(
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            product_name=product.name if product else None,
            quantity=item.quantity,
            unit_price=float(item.unit_price),
            subtotal=float(item.subtotal),
        ))

    payments = [
        PaymentResponse(
            payment_id=p.payment_id,
            order_id=p.order_id,
            status=p.status,
            payment_reference=p.payment_reference,
            amount=float(p.amount),
            payment_method=p.payment_method,
            created_at=p.created_at,
        )
        for p in order.payments
    ]

    shipments = [
        ShipmentResponse(
            shipment_id=s.shipment_id,
            tracking_number=s.tracking_number,
            carrier=s.carrier,
            status=s.status,
            estimated_delivery=s.estimated_delivery,
            shipped_at=s.shipped_at,
            delivered_at=s.delivered_at,
            created_at=s.created_at,
        )
        for s in order.shipments
    ]

    return OrderResponse(
        order_id=order.order_id,
        customer_id=order.customer_id,
        reservation_id=order.reservation_id,
        total_amount=float(order.total_amount),
        discount_amount=float(order.discount_amount) if order.discount_amount else 0.0,
        coupon_code=order.coupon_code,
        status=order.status,
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        shipments=shipments,
        payments=payments,
    )


@router.get("", response_model=List[OrderResponse])
def list_orders(
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.customer_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_build_order_response(o, db) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
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
    return _build_order_response(order, db)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    request: OrderCancelRequest = None,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(
        Order.order_id == order_id,
        Order.customer_id == customer.customer_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    cancellable = {"CONFIRMED", "PROCESSING"}
    if order.status not in cancellable:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order in status {order.status}"
        )

    order.status = "CANCELLED"
    db.commit()
    db.refresh(order)
    return _build_order_response(order, db)
