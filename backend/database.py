"""
database.py — подключение к PostgreSQL через SQLAlchemy.
Создаёт движок (engine) и фабрику сессий (SessionLocal).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# URL берём напрямую (для учебного проекта — ок, в проде — из .env)
DATABASE_URL = "postgresql://postgres:1127456@localhost:5432/discount_db"

engine = create_engine(DATABASE_URL, echo=False)

# autocommit=False — мы сами управляем транзакциями
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


def get_db():
    """
    Dependency для FastAPI: открывает сессию на время запроса,
    затем гарантированно закрывает её.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
