"""
Cart API — persistent cart stored in PostgreSQL.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_customer
from app.models.models import Cart, CartItem, Product, Inventory
from app.schemas.schemas import CartResponse, CartItemResponse, CartItemAdd, CartItemUpdate

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _get_or_create_cart(db: Session, customer_id: str) -> Cart:
    cart = db.query(Cart).filter(
        Cart.customer_id == customer_id,
        Cart.status == "ACTIVE"
    ).first()
    if not cart:
        cart = Cart(cart_id=str(uuid.uuid4()), customer_id=customer_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _build_cart_response(cart: Cart) -> CartResponse:
    items = []
    subtotal = 0.0
    for item in cart.items:
        sub = float(item.unit_price) * item.quantity
        subtotal += sub
        items.append(CartItemResponse(
            cart_item_id=item.cart_item_id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else None,
            product_image=item.product.image_url if item.product else None,
            quantity=item.quantity,
            unit_price=float(item.unit_price),
            subtotal=sub,
        ))
    return CartResponse(
        cart_id=cart.cart_id,
        customer_id=cart.customer_id,
        items=items,
        subtotal=round(subtotal, 2),
        item_count=len(items),
    )


@router.get("", response_model=CartResponse)
def get_cart(customer=Depends(get_current_customer), db: Session = Depends(get_db)):
    cart = _get_or_create_cart(db, customer.customer_id)
    db.refresh(cart)
    return _build_cart_response(cart)


@router.post("/items", response_model=CartResponse, status_code=201)
def add_to_cart(
    request: CartItemAdd,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.product_id == request.product_id,
        Product.status == "ACTIVE"
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    inv = db.query(Inventory).filter(Inventory.product_id == request.product_id).first()
    if not inv or inv.available_quantity < request.quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")

    cart = _get_or_create_cart(db, customer.customer_id)

    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.cart_id,
        CartItem.product_id == request.product_id,
    ).first()

    if existing:
        existing.quantity = min(10, existing.quantity + request.quantity)
    else:
        item = CartItem(
            cart_item_id=str(uuid.uuid4()),
            cart_id=cart.cart_id,
            product_id=request.product_id,
            quantity=request.quantity,
            unit_price=float(product.price),
        )
        db.add(item)

    db.commit()
    db.refresh(cart)
    return _build_cart_response(cart)


@router.put("/items/{cart_item_id}", response_model=CartResponse)
def update_cart_item(
    cart_item_id: str,
    request: CartItemUpdate,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    cart = _get_or_create_cart(db, customer.customer_id)
    item = db.query(CartItem).filter(
        CartItem.cart_item_id == cart_item_id,
        CartItem.cart_id == cart.cart_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    item.quantity = request.quantity
    db.commit()
    db.refresh(cart)
    return _build_cart_response(cart)


@router.delete("/items/{cart_item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_item_id: str,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    cart = _get_or_create_cart(db, customer.customer_id)
    item = db.query(CartItem).filter(
        CartItem.cart_item_id == cart_item_id,
        CartItem.cart_id == cart.cart_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()
    db.refresh(cart)
    return _build_cart_response(cart)


@router.delete("", status_code=204)
def clear_cart(customer=Depends(get_current_customer), db: Session = Depends(get_db)):
    cart = _get_or_create_cart(db, customer.customer_id)
    for item in cart.items:
        db.delete(item)
    db.commit()
