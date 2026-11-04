"""
Модель показания датчика.

Таблица telemetry: id, device_id, internal_device_id, sensor, value, recorded_at.
Внутреннее устройство контроллера идентифицируется полем internal_device_id
(0, 1, 2); отдельной таблицы internal_devices в минимальной версии нет.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from app.db.base import Base


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (
    Index("idx_telemetry_device_time", "device_id", "recorded_at"),
    )

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        comment="ID показания",
    )
    device_id = Column(
        BigInteger,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        comment="Контроллер, отправивший показание",
    )
    internal_device_id = Column(
        SmallInteger,
        nullable=False,
        comment="ID внутреннего устройства (0, 1, 2)",
    )
    sensor = Column(
        String(64),
        nullable=False,
        comment="Имя датчика (например, Temperature sensor)",
    )
    value = Column(
        Numeric(10, 3),
        nullable=False,
        comment="Значение показания",
    )
    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Время измерения",
    )

    # Связи
    device = relationship("Device", back_populates="telemetry")

    @property
    def serialize(self) -> dict:
        """Поля показания для ответа API."""
        return {
            "device_id": self.device_id,
            "internal_device_id": self.internal_device_id,
            "sensor": self.sensor,
            "value": float(self.value) if self.value is not None else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
