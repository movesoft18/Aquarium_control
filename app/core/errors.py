"""
Коды ошибок приложения и исключение AppError.

Коды фиксированы для всего проекта (см. соглашение о формате ответа API).
HTTP-статус хранится рядом с кодом, чтобы обработчик мог вернуть
правильный статус.
"""

from typing import Any


# Коды ошибок
ERROR_VALIDATION = 1001
ERROR_CREDENTIALS = 1002
ERROR_FORBIDDEN = 1003
ERROR_NOT_FOUND = 1004
ERROR_CONFLICT = 1005
ERROR_DEVICE_KEY = 1006
ERROR_COMMAND = 1007
ERROR_INTERNAL = 1008


class AppError(Exception):
    """
    Исключение приложения: код ошибки, сообщение, HTTP-статус, данные.

    Пример:
        raise AppError(ERROR_NOT_FOUND, "Device not found", 404)
    """

    def __init__(
        self,
        error: int,
        message: str,
        http_status: int = 400,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.http_status = http_status
        self.data = data