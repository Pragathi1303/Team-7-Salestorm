"""
Auth service — JWT-based authentication.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Customer
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def register_customer(db: Session, name: str, email: str, password: str, phone: Optional[str] = None) -> tuple[bool, str, Optional[Customer]]:
    if db.query(Customer).filter(Customer.email == email).first():
        return False, "email_already_registered", None

    customer = Customer(
        customer_id=str(uuid.uuid4()),
        name=name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role="CUSTOMER",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    logger.info("customer_registered", customer_id=customer.customer_id, email=email)
    return True, "registered", customer


def login_customer(db: Session, email: str, password: str) -> tuple[bool, str, Optional[str]]:
    customer = db.query(Customer).filter(Customer.email == email).first()
    if not customer:
        return False, "invalid_credentials", None
    if not customer.is_active:
        return False, "account_disabled", None
    if not verify_password(password, customer.password_hash):
        return False, "invalid_credentials", None

    token = create_access_token({
        "sub": customer.customer_id,
        "email": customer.email,
        "role": customer.role,
        "name": customer.name,
    })
    logger.info("customer_login", customer_id=customer.customer_id)
    return True, "ok", token


def get_customer_from_token(db: Session, token: str) -> Optional[Customer]:
    payload = decode_token(token)
    if not payload:
        return None
    customer_id = payload.get("sub")
    if not customer_id:
        return None
    return db.query(Customer).filter(Customer.customer_id == customer_id).first()
