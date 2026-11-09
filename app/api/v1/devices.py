"""
Роуты контроллеров: создание и список.

Оба эндпоинта требуют JWT: user = Depends(get_current_user).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, ErrorResponse, ValidationErrorResponse
from app.schemas.device import CreateDeviceRequest, DeviceCreatedData, DeviceListData
from app.services import devices as devices_service


router = APIRouter()


@router.post(
    "",
    status_code=201,
    response_model=ApiResponse[DeviceCreatedData],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing JWT"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
)
def create_device(
    payload: CreateDeviceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Создать контроллер.

    Ответ содержит data.api_key - показывается один раз.
    Ошибки: 1001 (422), 1002 (401) при неверном JWT.
    """
    device, api_key = devices_service.create(db, user.id, payload.name)
    return ok(
        {
            "id": device.id,
            "name": device.name,
            "api_key": api_key,
            "created_at": device.created_at.isoformat() if device.created_at else None,
        }
    )


@router.get(
    "",
    response_model=ApiResponse[DeviceListData],
    responses={401: {"model": ErrorResponse, "description": "Invalid or missing JWT"}},
)
def list_devices(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Список контроллеров текущего пользователя.

    Ответ: data.items - массив device.serialize.
    Ошибки: 1002 (401) при неверном JWT.
    """
    devices = devices_service.list_for_owner(db, user.id)
    return ok({"items": [d.serialize for d in devices]})