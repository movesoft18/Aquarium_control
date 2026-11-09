"""
Точка входа FastAPI.

Создаёт приложение, регистрирует обработчики исключений,
healthcheck и роуты /api/v1.

Запуск:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.responses import ok
from app.schemas.common import ApiResponse, HealthData


def create_app() -> FastAPI:
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="Aquarium API",
        version="1.0.0",
        description="API системы «Аквариум с удалённым доступом и мониторингом»",
    )

    # Единый формат ошибок для всех исключений.
    register_exception_handlers(app)

    @app.get("/health", response_model=ApiResponse[HealthData], tags=["service"])
    def health() -> dict:
        """Проверка живости приложения."""
        return ok({"status": "healthy"})

    # Роуты подключаются по мере реализации:
    from app.api.v1 import auth, devices, telemetry, commands
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(telemetry.router, prefix="/api/v1", tags=["telemetry"])
    app.include_router(commands.router, prefix="/api/v1", tags=["commands"])

    return app


app = create_app()