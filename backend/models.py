"""
models.py — ORM-модели SQLAlchemy.
Таблицы: users, products.
"""

from datetime import datetime
from sqlalchemy import (
    Integer, String, Float, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class User(Base):
    """Пользователь системы."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Связь «один ко многим» с Product
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="owner", cascade="all, delete-orphan"
    )


class Product(Base):
    """Товар в «Избранном» конкретного пользователя."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    old_price: Mapped[float] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    image_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)          # 0.0–5.0
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=True)   # кол-во отзывов
    # WB / Ozon / Ya
    marketplace_name: Mapped[str] = mapped_column(String(50), nullable=False, default="WB")
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship("User", back_populates="products")
