"""
schemas.py — Pydantic-схемы для валидации запросов и ответов API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ─────────────────────────── Auth ───────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─────────────────────────── Product ───────────────────────────

class ProductBase(BaseModel):
    title: str
    current_price: float
    old_price: Optional[float] = None
    url: str
    image_url: Optional[str] = None
    marketplace_name: str = "WB"


class ProductCreate(ProductBase):
    """Схема для добавления товара в избранное."""
    pass


class ProductOut(ProductBase):
    id: int
    user_id: int
    last_updated: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────── Search result ───────────────────────────

class SearchResult(BaseModel):
    """Один результат поиска (не сохранённый в БД)."""
    title: str
    current_price: float
    old_price: Optional[float] = None
    url: str
    image_url: Optional[str] = None
    marketplace_name: str
