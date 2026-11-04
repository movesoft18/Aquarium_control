"""
Безопасность: хеширование паролей, JWT, API-ключи устройств.

- Пароли: bcrypt через passlib (с солью, необратимо).
- JWT: python-jose, алгоритм HS256.
- API-ключи: случайная строка + детерминированный хеш с pepper
  (нужен для поиска устройства по ключу).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Контекст для хеширования паролей.
# bcrypt автоматически добавляет соль и хранит её в хеше.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хеширует пароль.

    Результат - строка, которую можно хранить в БД.
    Проверить пароль можно только через verify_password.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Проверяет пароль против хеша.

    Возвращает True, если пароль верный.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """
    Создаёт JWT с user_id и сроком действия.

    payload:
      sub - идентификатор пользователя (строка, требование JWT);
      exp - время истечения токена.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expires_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """
    Декодирует JWT и возвращает user_id.

    Возвращает None, если токен неверный, просрочен или без sub.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        # Неверная подпись, просроченный токен, некорректный формат.
        return None

    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except ValueError:
        return None


def generate_api_key() -> str:
    """
    Генерирует новый API-ключ устройства.

    Полное значение показывается пользователю один раз при создании
    контроллера. В БД хранится только хеш.
    """
    return "dk_live_" + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """
    Хеширует API-ключ с pepper.

    Хеш детерминированный: по одному и тому же ключу получается
    одинаковый хеш. Это нужно, чтобы находить устройство по ключу
    запросом WHERE api_key_hash = ....

    Pepper - секрет из настроек; без него хеш не воспроизвести.
    """
    data = (settings.api_key_pepper + api_key).encode("utf-8")
    return hashlib.sha256(data).hexdigest()