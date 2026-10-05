"""
Auth API — register, login, logout, me.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.services.auth_service import register_customer, login_customer, get_customer_from_token
from app.schemas.schemas import RegisterRequest, LoginRequest, TokenResponse, CustomerResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_customer(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Extract and validate JWT from Authorization: Bearer <token> header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    customer = get_customer_from_token(db, token)
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not customer.is_active:
        raise HTTPException(status_code=401, detail="Account disabled")
    return customer


def get_current_admin(customer=Depends(get_current_customer)):
    if customer.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return customer


def get_optional_customer(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Returns customer or None — for endpoints that work both authenticated and not."""
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return get_customer_from_token(db, token)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    success, message, customer = register_customer(
        db, request.name, request.email, request.password, request.phone
    )
    if not success:
        if message == "email_already_registered":
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=400, detail=message)

    from app.services.auth_service import create_access_token
    token = create_access_token({
        "sub": customer.customer_id,
        "email": customer.email,
        "role": customer.role,
        "name": customer.name,
    })
    return TokenResponse(
        access_token=token,
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        role=customer.role,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    success, message, token = login_customer(db, request.email, request.password)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    from app.services.auth_service import decode_token
    payload = decode_token(token)
    from app.models.models import Customer
    customer = db.query(Customer).filter(Customer.customer_id == payload["sub"]).first()

    return TokenResponse(
        access_token=token,
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        role=customer.role,
    )


@router.post("/logout")
def logout():
    # JWT is stateless — client discards token
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=CustomerResponse)
def me(customer=Depends(get_current_customer)):
    return customer
