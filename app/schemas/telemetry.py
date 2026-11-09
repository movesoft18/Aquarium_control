"""
Схемы телеметрии.

TelemetryReading  - одно показание в запросе от контроллера.
TelemetryRequest  - тело запроса POST /telemetry.
TelemetryData     - показание в ответе API.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TelemetryReading(BaseModel):
    """Одно показание датчика в запросе контроллера."""
    # ID внутреннего устройства контроллера (0, 1, 2).
    internal_device_id: int
    # Имя датчика, например "Temperature sensor".
    sensor: str = Field(min_length=1, max_length=64)
    # Значение показания.
    value: float


class TelemetryRequest(BaseModel):
    """Тело запроса POST /telemetry."""
    # ID контроллера. Должен совпадать с устройством из X-Device-Key.
    device_id: int
    # Время измерения. Если не передано, сервер подставит текущее время.
    recorded_at: datetime | None = None
    # Список показаний. Минимум одно.
    readings: list[TelemetryReading] = Field(min_length=1)


class TelemetryData(BaseModel):
    """Показание в ответе API."""
    device_id: int
    internal_device_id: int
    sensor: str
    value: float
    recorded_at: str

class TelemetrySavedData(BaseModel):
    """Результат приёма телеметрии."""
    saved: int