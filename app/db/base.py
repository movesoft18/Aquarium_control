"""
Базовый класс моделей SQLAlchemy.

Все модели наследуются от Base. Здесь же — engine и фабрика сессий.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


# Engine: пул соединений к MySQL.
# pool_pre_ping=True проверяет соединение перед использованием —
# полезно, если MySQL перезапускается.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

# Фабрика сессий: каждая сессия — отдельная транзакция.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)