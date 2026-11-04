"""
Модель пользователя (владельца аквариума).

Таблица users: id, email, password_hash, created_at.
Пароль хранится только в виде хеша; в ответ API не попадает.
"""

from sqlalchemy import BigInteger, Column, DateTime, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        comment="ID пользователя",
    )
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="Email для входа",
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Хеш пароля (bcrypt/argon2)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Дата регистрации",
    )

    # Связи
    devices = relationship(
        "Device",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    @property
    def serialize(self) -> dict:
        """Поля пользователя для ответа API (без password_hash)."""
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }