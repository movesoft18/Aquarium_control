"""
Зависимости FastAPI: текущий пользователь и текущее устройство.

- get_current_user: JWT из заголовка Authorization: Bearer .
- get_current_device: API-ключ из заголовка X-Device-Key.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import (
    AppError,
    ERROR_CREDENTIALS,
    ERROR_DEVICE_KEY,
)
from app.core.security import decode_access_token, hash_api_key
from app.db.session import get_db
from app.models.device import Device
from app.models.user import User
from app.repositories import devices as devices_repo
from app.repositories import users as users_repo


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    Извлекает пользователя из JWT.

    Заголовок: Authorization: Bearer .
    Ошибка 1002 (401), если заголовка нет, токен неверный или просрочен.
    """
    # Проверяем наличие заголовка и префикса Bearer.
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(ERROR_CREDENTIALS, "Invalid credentials", 401)

    # Отделяем сам токен от префикса.
    token = authorization.removeprefix("Bearer ").strip()

    # Декодируем; при ошибке получаем None.
    user_id = decode_access_token(token)
    if user_id is None:
        raise AppError(ERROR_CREDENTIALS, "Invalid or expired token", 401)

    # Загружаем пользователя; если его нет - токен ссылается на удалённого.
    user = users_repo.get_by_id(db, user_id)
    if user is None:
        raise AppError(ERROR_CREDENTIALS, "User not found", 401)
    return user


def get_current_device(
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    db: Session = Depends(get_db),
) -> Device:
    """
    Извлекает устройство по API-ключу.

    Заголовок: X-Device-Key: .
    Ошибка 1006 (401), если ключа нет или он неверный.
    """
    if not x_device_key:
        raise AppError(ERROR_DEVICE_KEY, "Invalid device key", 401)

    # Хешируем ключ и ищем устройство по хешу.
    api_key_hash = hash_api_key(x_device_key)
    device = devices_repo.get_by_api_key_hash(db, api_key_hash)
    if device is None:
        raise AppError(ERROR_DEVICE_KEY, "Invalid device key", 401)
    return device