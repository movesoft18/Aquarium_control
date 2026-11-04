"""
Сервис телеметрии: приём показаний и выдача последнего.

Проверки:
  - device_id в теле совпадает с устройством из X-Device-Key (1003);
  - владелец запрашивает только свой контроллер (1003);
  - у контроллера есть показания (1004).
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import (
    AppError,
    ERROR_FORBIDDEN,
    ERROR_NOT_FOUND,
)
from app.models.device import Device
from app.models.telemetry import Telemetry
from app.repositories import devices as devices_repo
from app.repositories import telemetry as telemetry_repo
from app.schemas.telemetry import TelemetryRequest


def ingest(
    db: Session,
    device: Device,
    payload: TelemetryRequest,
) -> int:
    """
    Принимает телеметрию от контроллера.

    device - устройство, найденное по X-Device-Key.
    Если device_id в теле не совпадает с устройством из ключа,
    возвращается 1003 (доступ запрещён): контроллер не может
    писать от имени другого контроллера.

    Возвращает количество сохранённых показаний.
    """
    # Проверка: тело относится к тому же контроллеру, что и ключ.
    if payload.device_id != device.id:
        raise AppError(ERROR_FORBIDDEN, "Device mismatch", 403)

    # Время измерения: из тела или текущее.
    recorded_at = payload.recorded_at or datetime.now(timezone.utc)

    # Формируем записи для сохранения.
    records = [
        Telemetry(
            device_id=device.id,
            internal_device_id=r.internal_device_id,
            sensor=r.sensor,
            value=r.value,
            recorded_at=recorded_at,
        )
        for r in payload.readings
    ]

    # Сохраняем показания.
    saved = telemetry_repo.create_many(db, records)

    # Обновляем время последней связи контроллера.
    devices_repo.touch_last_seen(db, device, recorded_at)
    db.commit()

    return saved


def get_latest(db: Session, owner_id: int, device_id: int) -> Telemetry:
    """
    Возвращает последнее показание по контроллеру владельца.

    Ошибки:
      1003 - контроллер принадлежит другому пользователю;
      1004 - контроллер не найден или показаний ещё нет.
    """
    device = devices_repo.get_by_id(db, device_id)
    if device is None:
        raise AppError(ERROR_NOT_FOUND, "Device not found", 404)

    # Проверка владения: owner видит только свои контроллеры.
    if device.owner_id != owner_id:
        raise AppError(ERROR_FORBIDDEN, "Access denied", 403)

    latest = telemetry_repo.get_latest_by_device(db, device_id)
    if latest is None:
        raise AppError(ERROR_NOT_FOUND, "No telemetry yet", 404)
    return latest
