"""
Модель команды управления.

Таблица commands: id, device_id, internal_device_id, type, state, status,
created_at, executed_at.
В минимальной версии поддерживается только type='switch' для внутренних
устройств 0 и 1 (Air pump, Light).
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from app.db.base import Base


class Command(Base):
    __tablename__ = "commands"
    __table_args__ = (
    Index("idx_commands_device_status", "device_id", "status"),
    CheckConstraint("state IN (0, 1)", name="chk_commands_state"),
    CheckConstraint(
        "status IN ('pending','done','failed')",
        name="chk_commands_status",
    ),
    )

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        comment="ID команды",
    )
    device_id = Column(
        BigInteger,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        comment="Контроллер, которому адресована команда",
    )
    internal_device_id = Column(
        SmallInteger,
        nullable=False,
        comment="ID внутреннего устройства (0 или 1 для switch)",
    )
    type = Column(
        String(32),
        nullable=False,
        comment="Тип команды: switch",
    )
    state = Column(
        SmallInteger,
        nullable=False,
        comment="Целевое состояние: 0 — выключить, 1 — включить",
    )
    status = Column(
        String(16),
        nullable=False,
        server_default="pending",
        comment="Статус выполнения: pending, done, failed",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания команды",
    )
    executed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время подтверждения выполнения",
    )

    # Связи
    device = relationship("Device", back_populates="commands")

    @property
    def serialize(self) -> dict:
        """Поля команды для ответа API."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "internal_device_id": self.internal_device_id,
            "type": self.type,
            "state": self.state,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }