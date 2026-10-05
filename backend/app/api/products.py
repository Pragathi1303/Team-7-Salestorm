"""
Products API — list, search, filter, sort, detail, admin CRUD.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from app.core.database import get_db
from app.api.auth import get_current_customer, get_optional_customer
from app.services.product_service import (
    get_all_products, get_product_cached, get_active_sale_for_product, get_inventory
)
from app.models.models import Product, Category, Inventory, Sale
from app.schemas.schemas import (
    ProductResponse, ProductWithSaleResponse, ProductCreate, ProductUpdate, CategoryResponse
)

router = APIRouter(prefix="/api/products", tags=["products"])


def _enrich(p: Product, db: Session) -> dict:
    """Add sale + inventory info to a product dict."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        sale = loop.run_until_complete(get_active_sale_for_product(db, p.product_id))
    except Exception:
        sale = None
    finally:
        loop.close()
    inv = get_inventory(db, p.product_id)
    cat = db.query(Category).filter(Category.category_id == p.category_id).first() if p.category_id else None
    return {
        "product_id": p.product_id,
        "name": p.name,
        "description": p.description,
        "price": float(p.price),
        "sku": p.sku,
        "status": p.status,
        "category_id": p.category_id,
        "image_url": p.image_url,
        "brand": p.brand,
        "sale_price": sale["sale_price"] if sale else None,
        "sale_id": sale["sale_id"] if sale else None,
        "sale_end_time": sale["end_time"] if sale else None,
        "sale_name": sale["sale_name"] if sale else None,
        "available_quantity": inv.available_quantity if inv else 0,
        "reserved_quantity": inv.reserved_quantity if inv else 0,
        "sold_quantity": inv.sold_quantity if inv else 0,
        "category_name": cat.category_name if cat else None,
    }


@router.get("", response_model=List[ProductWithSaleResponse])
async def list_products(
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    sort_by: Optional[str] = Query("name"),  # name | price | stock
    sort_order: Optional[str] = Query("asc"),
    on_sale: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.status == "ACTIVE")

    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if sort_by == "price":
        query = query.order_by(Product.price.asc() if sort_order == "asc" else Product.price.desc())
    else:
        query = query.order_by(Product.name.asc() if sort_order == "asc" else Product.name.desc())

    products = query.all()
    result = []
    for p in products:
        sale = await get_active_sale_for_product(db, p.product_id)
        if on_sale is True and not sale:
            continue
        if on_sale is False and sale:
            continue
        inv = get_inventory(db, p.product_id)
        cat = db.query(Category).filter(Category.category_id == p.category_id).first() if p.category_id else None
        result.append(ProductWithSaleResponse(
            product_id=p.product_id,
            name=p.name,
            description=p.description,
            price=float(p.price),
            sku=p.sku,
            status=p.status,
            category_id=p.category_id,
            image_url=p.image_url,
            brand=p.brand,
            sale_price=sale["sale_price"] if sale else None,
            sale_id=sale["sale_id"] if sale else None,
            sale_end_time=sale["end_time"] if sale else None,
            sale_name=sale["sale_name"] if sale else None,
            available_quantity=inv.available_quantity if inv else 0,
            reserved_quantity=inv.reserved_quantity if inv else 0,
            sold_quantity=inv.sold_quantity if inv else 0,
            category_name=cat.category_name if cat else None,
        ))
    return result


@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).all()


@router.get("/{product_id}", response_model=ProductWithSaleResponse)
async def get_product(product_id: str, db: Session = Depends(get_db)):
    product = await get_product_cached(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sale = await get_active_sale_for_product(db, product_id)
    inv = get_inventory(db, product_id)
    p = db.query(Product).filter(Product.product_id == product_id).first()
    cat = db.query(Category).filter(Category.category_id == p.category_id).first() if p and p.category_id else None

    return ProductWithSaleResponse(
        **product,
        sale_price=sale["sale_price"] if sale else None,
        sale_id=sale["sale_id"] if sale else None,
        sale_end_time=sale["end_time"] if sale else None,
        sale_name=sale["sale_name"] if sale else None,
        available_quantity=inv.available_quantity if inv else 0,
        reserved_quantity=inv.reserved_quantity if inv else 0,
        sold_quantity=inv.sold_quantity if inv else 0,
        category_name=cat.category_name if cat else None,
    )


# ── Admin product CRUD ────────────────────────────────────────────────────────

@router.post("", response_model=ProductWithSaleResponse, status_code=201)
def create_product(
    request: ProductCreate,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if customer.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    if db.query(Product).filter(Product.sku == request.sku).first():
        raise HTTPException(status_code=409, detail="SKU already exists")

    product = Product(
        product_id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        price=request.price,
        sku=request.sku,
        category_id=request.category_id,
        image_url=request.image_url,
        brand=request.brand,
        status="ACTIVE",
    )
    db.add(product)
    db.flush()

    inv = Inventory(
        inventory_id=str(uuid.uuid4()),
        product_id=product.product_id,
        available_quantity=request.initial_stock,
        reserved_quantity=0,
        sold_quantity=0,
        version=1,
    )
    db.add(inv)
    db.commit()
    db.refresh(product)

    return ProductWithSaleResponse(
        product_id=product.product_id,
        name=product.name,
        description=product.description,
        price=float(product.price),
        sku=product.sku,
        status=product.status,
        category_id=product.category_id,
        image_url=product.image_url,
        brand=product.brand,
        available_quantity=request.initial_stock,
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    request: ProductUpdate,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if customer.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in request.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def deactivate_product(
    product_id: str,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if customer.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.status = "INACTIVE"
    db.commit()
