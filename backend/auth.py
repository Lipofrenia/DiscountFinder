"""
auth.py — утилиты JWT и хэширования паролей.

Используем sha256_crypt вместо bcrypt:
  - нет ограничения длины пароля в 72 байта
  - нет конфликтов версий с bcrypt 4.x
  - встроен в passlib без дополнительных зависимостей
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models

# ── Секрет и алгоритм — в продакшене хранить в .env ──
SECRET_KEY = "discount-sleuth-super-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# sha256_crypt: надёжен, без ограничений bcrypt, без зависимостей
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    """Хэшируем пароль через sha256_crypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Проверяем пароль против хэша."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создаём JWT-токен с временем жизни."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Dependency: декодирует JWT из заголовка Authorization,
    возвращает объект пользователя из БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
