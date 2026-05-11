# Скидочный сыщик 🔍

Учебный fullstack-проект: FastAPI + PostgreSQL + Flet.

## Структура

```
DiscountFinder/
├── backend/
│   ├── __init__.py
│   ├── database.py     # Подключение к PostgreSQL
│   ├── models.py       # SQLAlchemy ORM-модели
│   ├── schemas.py      # Pydantic-схемы
│   ├── auth.py         # JWT + passlib
│   ├── services.py     # ParserService + мониторинг цен
│   └── main.py         # FastAPI точка входа
├── frontend/
│   └── app.py          # Flet Desktop UI
├── requirements.txt
└── .env.example
```

## Быстрый старт

### 1. Создать базу данных PostgreSQL
```sql
CREATE DATABASE discount_db;
```

### 2. Создать и активировать venv
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Установить зависимости
```powershell
pip install -r requirements.txt
```

### 4. Запустить бэкенд (из корня проекта)
```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
> Таблицы создадутся автоматически при первом запуске.  
> Документация API: http://127.0.0.1:8000/docs

### 5. Запустить фронтенд (в отдельном терминале)
```powershell
python frontend/app.py
```

## API-эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход, возвращает JWT |
| GET | `/search?q=...` | Поиск товаров (мок) |
| GET | `/favorites` | Список избранного |
| POST | `/favorites` | Добавить товар |
| DELETE | `/favorites/{id}` | Удалить товар |
