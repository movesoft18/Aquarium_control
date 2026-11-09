"""
Схемы команд.

CreateCommandRequest - тело POST /devices/{id}/commands.
CommandData          - команда в ответе API.
CommandAckRequest    - тело PATCH /commands/{id}.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CreateCommandRequest(BaseModel):
    """
    Тело запроса на создание команды.

    В минимальной версии поддерживается только type="switch".
    state: 0 - выключить, 1 - включить.
    internal_device_id: 0 (Air pump) или 1 (Light).
    """
    internal_device_id: int = Field(ge=0)
    type: Literal["switch"] = "switch"
    state: Literal[0, 1]


class CommandData(BaseModel):
    """Команда в ответе API."""
    id: int
    device_id: int
    internal_device_id: int
    type: str
    state: int
    status: str
    created_at: str
    executed_at: str | None = None


class CommandAckRequest(BaseModel):
    """
    Тело подтверждения команды контроллером.

    status: "done" или "failed".
    result: необязательные детали выполнения (пишутся в лог).
    """
    status: Literal["done", "failed"]

class CommandListData(BaseModel):
    """Обёртка для списка ожидающих команд."""
    items: list[CommandData]

class CommandAckData(BaseModel):
    """Результат подтверждения команды."""
    id: int
    status: str
    executed_at: str | None = None