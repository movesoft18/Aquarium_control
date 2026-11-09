"""
Схемы контроллера.
"""

from pydantic import BaseModel, Field


class CreateDeviceRequest(BaseModel):
    """Тело запроса POST /devices."""
    # Имя контроллера: от 1 до 120 символов.
    name: str = Field(min_length=1, max_length=120)


class DeviceCreatedData(BaseModel):
    """Данные ответа на создание контроллера."""
    id: int
    name: str
    # api_key показывается только один раз при создании.
    api_key: str
    created_at: str


class DeviceData(BaseModel):
    """Данные контроллера в списке."""
    id: int
    name: str
    # last_seen_at пустой, пока контроллер не отправил телеметрию.
    last_seen_at: str | None = None
    created_at: str

class DeviceListData(BaseModel):
    """Обёртка для списка контроллеров."""
    items: list[DeviceData]