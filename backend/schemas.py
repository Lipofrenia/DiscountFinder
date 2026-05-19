

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr




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




class PriceHistoryOut(BaseModel):
    id: int
    price: float
    checked_at: datetime

    model_config = {"from_attributes": True}




class ProductBase(BaseModel):
    title: str
    current_price: float
    old_price: Optional[float] = None
    url: str
    image_url: Optional[str] = None
    marketplace_name: str = "WB"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    user_id: int
    last_updated: datetime
    price_history: List[PriceHistoryOut] = []

    model_config = {"from_attributes": True}




class SearchResult(BaseModel):
    title: str
    current_price: float
    old_price: Optional[float] = None
    url: str
    image_url: Optional[str] = None
    marketplace_name: str
    rating: Optional[float] = None
    reviews_count: Optional[int] = None

