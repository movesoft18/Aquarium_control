"""
Роуты телеметрии.

POST /telemetry - контроллер, X-Device-Key.
GET  /devices/{device_id}/telemetry/latest - владелец, JWT.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_device, get_current_user
from app.core.responses import ok
from app.db.session import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.telemetry import TelemetryRequest
from app.services import telemetry as telemetry_service


router = APIRouter()


@router.post("/telemetry", status_code=201)
def send_telemetry(
    payload: TelemetryRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> dict:
    """
    Приём телеметрии от контроллера.

    Авторизация: X-Device-Key.
    Ошибки:
      1001 (422) - невалидное тело;
      1003 (403) - device_id не совпадает с ключом;
      1006 (401) - неверный X-Device-Key.
    """
    saved = telemetry_service.ingest(db, device, payload)
    return ok({"saved": saved})


@router.get("/devices/{device_id}/telemetry/latest")
def get_latest_telemetry(
    device_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Последнее показание по контроллеру.

    Авторизация: JWT (owner).
    Ошибки:
      1002 (401) - нет или неверный JWT;
      1003 (403) - контроллер принадлежит другому владельцу;
      1004 (404) - контроллер не найден или показаний нет.
    """
    latest = telemetry_service.get_latest(db, user.id, device_id)
    return ok(latest.serialize)