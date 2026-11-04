"""
Модель контроллера аквариума.

Таблица devices: id, owner_id, name, api_key_hash, last_seen_at, created_at.
API-ключ хранится только в виде хеша; полное значение показывается
один раз при создании контроллера.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
    Index("idx_devices_owner", "owner_id"),
    )

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        comment="ID контроллера",
    )
    owner_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Владелец контроллера",
    )
    name = Column(
        String(120),
        nullable=False,
        comment="Название контроллера",
    )
    api_key_hash = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="Хеш API-ключа устройства",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последней телеметрии",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Дата создания",
    )

    # Связи
    owner = relationship("User", back_populates="devices")
    telemetry = relationship(
        "Telemetry",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    commands = relationship(
        "Command",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    @property
    def serialize(self) -> dict:
        """Поля контроллера для ответа API (без api_key_hash)."""
        return {
            "id": self.id,
            "name": self.name,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
