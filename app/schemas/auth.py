"""
Схемы регистрации и входа.

Pydantic-схемы описывают формат данных на границе API.
Они не знают о БД и не содержат бизнес-логики.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Тело запроса POST /auth/register."""
    # EmailStr проверяет формат email; при ошибке FastAPI вернёт 422.
    email: EmailStr
    # Пароль: минимум 8 символов, максимум 128.
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Тело запроса POST /auth/login."""
    email: EmailStr
    password: str


class TokenData(BaseModel):
    """Данные успешного входа: JWT и тип токена."""
    access_token: str
    token_type: str = "bearer"

class UserData(BaseModel):
    """Пользователь в ответе на регистрацию."""
    id: int
    email: str
    created_at: str    