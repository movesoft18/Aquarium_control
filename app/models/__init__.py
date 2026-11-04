"""
Пакет моделей. Импорт всех моделей нужен, чтобы Alembic
видел их при autogenerate.
"""

from app.models.user import User
from app.models.device import Device
from app.models.telemetry import Telemetry
from app.models.command import Command

__all__ = ["User", "Device", "Telemetry", "Command"]