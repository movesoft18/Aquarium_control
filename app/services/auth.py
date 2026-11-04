"""
Сервис аутентификации: регистрация и вход.

Здесь бизнес-правила: email должен быть уникальным,
пароль должен совпадать с хешем.
"""

from sqlalchemy.orm import Session

from app.core.errors import (
    AppError,
    ERROR_CONFLICT,
    ERROR_CREDENTIALS,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories import users as users_repo


def register(db: Session, email: str, password: str) -> User:
    """
    Регистрирует пользователя.

    Ошибка 1005 (409), если email уже занят.
    Пароль хешируется перед сохранением.
    """
    existing = users_repo.get_by_email(db, email)
    if existing is not None:
        raise AppError(ERROR_CONFLICT, "Email already registered", 409)

    password_hash = hash_password(password)
    return users_repo.create(db, email, password_hash)


def login(db: Session, email: str, password: str) -> str:
    """
    Проверяет учётные данные и возвращает JWT.

    Ошибка 1002 (401), если email не найден или пароль неверный.
    Сообщение намеренно не уточняет, что именно неверно.
    """
    user = users_repo.get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(ERROR_CREDENTIALS, "Invalid credentials", 401)
    return create_access_token(user.id)