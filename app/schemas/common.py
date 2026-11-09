"""
Общие схемы ответов.

ApiResponse - обёртка для всех успешных ответов.
ErrorResponse - обёртка для ошибок без деталей.
ValidationErrorResponse - ошибка валидации с полями.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Успешный ответ: error=0, message, data."""
    error: int = 0
    message: str = "OK"
    data: T | None = None


class ErrorResponse(BaseModel):
    error: int
    message: str
    data: None = None


class ValidationErrorResponse(BaseModel):
    """Ответ с ошибкой валидации: детали в data.fields."""
    error: int = 1001
    message: str = "Validation error"
    data: dict

class HealthData(BaseModel):
    status: str