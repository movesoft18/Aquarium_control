"""
Сервис контроллеров: создание и список.

Создание генерирует API-ключ, хеширует его и сохраняет устройство.
Ключ возвращается вызывающему коду один раз.
"""

from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.models.device import Device
from app.repositories import devices as devices_repo


def create(db: Session, owner_id: int, name: str) -> tuple[Device, str]:
    """
    Создаёт контроллер и возвращает (device, api_key).

    api_key показывается один раз; в БД хранится только хеш.
    """
    # Генерируем ключ и сразу хешируем его для хранения.
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    device = devices_repo.create(db, owner_id, name, api_key_hash)

    # Возвращаем устройство и полный ключ - вызывающий код отдаст его клиенту.
    return device, api_key


def list_for_owner(db: Session, owner_id: int) -> list[Device]:
    """Возвращает контроллеры владельца."""
    return devices_repo.list_by_owner(db, owner_id)