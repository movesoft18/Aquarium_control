"""
Хелперы для формирования ответов по соглашению о формате ответа API.

Успешный ответ:
    {"error": 0, "message": "OK", "data": ...}

Ошибки формируются обработчиками исключений (см. exception_handlers.py).
"""

from typing import Any


def ok(data: Any = None, message: str = "OK") -> dict[str, Any]:
    """
    Успешный ответ.

    Пример:
        return ok({"id": 1, "email": "user@example.com"})
    """
    return {"error": 0, "message": message, "data": data}


def error_body(error: int, message: str, data: Any = None) -> dict[str, Any]:
    """
    Тело ответа с ошибкой. Используется обработчиками исключений.
    """
    return {"error": error, "message": message, "data": data}