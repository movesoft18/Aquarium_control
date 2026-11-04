"""
Сервис команд: создание, выдача, подтверждение.

Проверки:
  - владелец создаёт команду только для своего контроллера (1003);
  - internal_device_id - это switch, а не sensor (1007);
  - state равен 0 или 1 (проверяется схемой, 1001);
  - контроллер подтверждает только свою команду (1003);
  - команда существует (1004);
  - статус подтверждения - done или failed (проверяется схемой, 1001).
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import (
    AppError,
    ERROR_COMMAND,
    ERROR_FORBIDDEN,
    ERROR_NOT_FOUND,
)
from app.models.command import Command
from app.models.device import Device
from app.repositories import commands as commands_repo
from app.repositories import devices as devices_repo
from app.schemas.command import CommandAckRequest, CreateCommandRequest


# Внутренние устройства контроллера (см. модель устройства в эмуляторе).
# В минимальной версии список фиксирован: 0 и 1 - switch, 2 - sensor.
# Проверка нужна, потому что в БД нет таблицы internal_devices.
_SWITCH_IDS = {0, 1}
_SENSOR_IDS = {2}


def create_for_owner(
    db: Session,
    owner_id: int,
    device_id: int,
    payload: CreateCommandRequest,
) -> Command:
    """
    Создаёт команду для контроллера владельца.

    Ошибки:
      1003 - контроллер принадлежит другому пользователю;
      1004 - контроллер не найден;
      1007 - internal_device_id указывает на sensor или неизвестен.
    """
    device = devices_repo.get_by_id(db, device_id)
    if device is None:
        raise AppError(ERROR_NOT_FOUND, "Device not found", 404)

    # Проверка владения: owner управляет только своими контроллерами.
    if device.owner_id != owner_id:
        raise AppError(ERROR_FORBIDDEN, "Access denied", 403)

    # Проверка типа устройства: переключать можно только switch.
    if payload.internal_device_id not in _SWITCH_IDS:
        raise AppError(
            ERROR_COMMAND,
            f"Device {payload.internal_device_id} is not a switch",
            422,
        )

    return commands_repo.create(
        db,
        device_id=device.id,
        internal_device_id=payload.internal_device_id,
        type_=payload.type,
        state=payload.state,
    )


def list_pending_for_device(
    db: Session,
    device: Device,
    device_id: int,
) -> list[Command]:
    """
    Возвращает ожидающие команды контроллера.

    Контроллер может запрашивать команды только для себя:
    device_id в пути должен совпадать с устройством из X-Device-Key.
    Иначе - 1003.
    """
    if device.id != device_id:
        raise AppError(ERROR_FORBIDDEN, "Device mismatch", 403)
    return commands_repo.list_pending_for_device(db, device.id)


def ack(
    db: Session,
    device: Device,
    command_id: int,
    payload: CommandAckRequest,
) -> Command:
    """
    Подтверждает выполнение команды контроллером.

    Ошибки:
      1003 - команда принадлежит другому контроллеру;
      1004 - команда не найдена.
    """
    command = commands_repo.get_by_id(db, command_id)
    if command is None:
        raise AppError(ERROR_NOT_FOUND, "Command not found", 404)

    # Проверка принадлежности: контроллер подтверждает только свои команды.
    if command.device_id != device.id:
        raise AppError(ERROR_FORBIDDEN, "Access denied", 403)

    return commands_repo.mark_status(
        db,
        command,
        status=payload.status,
        when=datetime.now(timezone.utc),
    )