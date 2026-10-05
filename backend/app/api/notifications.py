"""
Notifications API.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_customer
from app.models.models import Notification
from app.schemas.schemas import NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    notifications = (
        db.query(Notification)
        .filter(Notification.customer_id == customer.customer_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return notifications


@router.get("/unread-count")
def unread_count(customer=Depends(get_current_customer), db: Session = Depends(get_db)):
    count = db.query(Notification).filter(
        Notification.customer_id == customer.customer_id,
        Notification.is_read == False,
    ).count()
    return {"unread_count": count}


@router.put("/{notification_id}/read")
def mark_read(
    notification_id: str,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.customer_id == customer.customer_id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"message": "Marked as read"}


@router.put("/read-all")
def mark_all_read(customer=Depends(get_current_customer), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.customer_id == customer.customer_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


def create_notification(
    db: Session,
    customer_id: str,
    notification_type: str,
    title: str,
    message: str,
    order_id: str = None,
):
    """Helper to create a notification record."""
    n = Notification(
        notification_id=str(uuid.uuid4()),
        customer_id=customer_id,
        order_id=order_id,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False,
        status="SENT",
    )
    db.add(n)
    # Caller must commit
