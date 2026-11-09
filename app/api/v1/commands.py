"""
Роуты команд.

POST  /devices/{device_id}/commands - владелец, JWT.
GET   /devices/{device_id}/commands - контроллер, X-Device-Key.
PATCH /commands/{command_id}         - контроллер, X-Device-Key.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_device, get_current_user
from app.core.responses import ok
from app.db.session import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.command import (
    CommandAckData,
    CommandAckRequest,
    CommandData,
    CommandListData,
    CreateCommandRequest,
)
from app.schemas.common import ApiResponse, ErrorResponse, ValidationErrorResponse
from app.services import commands as commands_service


router = APIRouter()


@router.post(
    "/devices/{device_id}/commands",
    status_code=201,
    response_model=ApiResponse[CommandData],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing JWT"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Device not found"},
        422: {"model": ValidationErrorResponse, "description": "Not a switch or invalid state"},
    },
)
def create_command(
    device_id: int,
    payload: CreateCommandRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Создать команду управления.

    Авторизация: JWT (owner).
    Ошибки:
      1001 (422) - невалидное тело;
      1002 (401) - нет или неверный JWT;
      1003 (403) - чужой контроллер;
      1004 (404) - контроллер не найден;
      1007 (422) - internal_device_id указывает на sensor.
    """
    command = commands_service.create_for_owner(db, user.id, device_id, payload)
    return ok(command.serialize)


@router.get(
    "/devices/{device_id}/commands",
    response_model=ApiResponse[CommandListData],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid device key"},
        403: {"model": ErrorResponse, "description": "Device mismatch"},
    },
)
def list_pending_commands(
    device_id: int,
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> dict:
    """
    Ожидающие команды для контроллера.

    Авторизация: X-Device-Key.
    Ошибки:
      1003 (403) - device_id в пути не совпадает с ключом;
      1006 (401) - неверный X-Device-Key.
    """
    commands = commands_service.list_pending_for_device(db, device, device_id)
    return ok({"items": [c.serialize for c in commands]})


@router.patch(
    "/commands/{command_id}",
    response_model=ApiResponse[CommandAckData],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid device key"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Command not found"},
        422: {"model": ValidationErrorResponse, "description": "Invalid status"},
    },
)
def ack_command(
    command_id: int,
    payload: CommandAckRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> dict:
    """
    Подтвердить выполнение команды.

    Авторизация: X-Device-Key.
    Ошибки:
      1001 (422) - невалидный статус;
      1003 (403) - команда принадлежит другому контроллеру;
      1004 (404) - команда не найдена;
      1006 (401) - неверный X-Device-Key.
    """
    command = commands_service.ack(db, device, command_id, payload)
    return ok(
        {
            "id": command.id,
            "status": command.status,
            "executed_at": command.executed_at.isoformat() if command.executed_at else None,
        }
    )