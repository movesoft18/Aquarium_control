"""
Обработчики исключений FastAPI.

Приводят все ошибки к единому формату:
    {"error": <код>, "message": "<текст>", "data": <данные или null>}

Коды:
    1001 — валидация
    1002 — учётные данные / токен
    1003 — доступ запрещён
    1004 — не найдено
    1005 — конфликт
    1006 — ключ устройства
    1007 — недопустимая команда
    1008 — внутренняя ошибка
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    AppError,
    ERROR_CREDENTIALS,
    ERROR_FORBIDDEN,
    ERROR_NOT_FOUND,
    ERROR_CONFLICT,
    ERROR_VALIDATION,
    ERROR_INTERNAL,
)

_HTTP_TO_ERROR = {
    401: ERROR_CREDENTIALS,
    403: ERROR_FORBIDDEN,
    404: ERROR_NOT_FOUND,
    409: ERROR_CONFLICT,
    422: ERROR_VALIDATION,
}

from app.core.responses import error_body

log = logging.getLogger("app.errors")


def _fields_from_validation(exc: RequestValidationError) -> dict[str, str]:
    """
    Преобразует ошибки Pydantic в словарь {поле: сообщение}.
    Поле берётся из loc (последний элемент пути).
    """
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        field = ".".join(str(p) for p in loc if p not in ("body", "query", "path"))
        fields[field or "body"] = err.get("msg", "invalid value")
    return fields


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует все обработчики исключений на приложении."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_body(exc.error, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                ERROR_VALIDATION,
                "Validation error",
                {"fields": _fields_from_validation(exc)},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        error = _HTTP_TO_ERROR.get(exc.status_code, ERROR_INTERNAL)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(error, str(exc.detail), None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Логируем трассировку, клиенту отдаём общий код.
        log.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=error_body(ERROR_INTERNAL, "Internal server error", None),
        )