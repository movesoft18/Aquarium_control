"""
Зависимость FastAPI для получения сессии БД.

Сессия создаётся на время запроса и закрывается после ответа.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()