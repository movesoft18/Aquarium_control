"""
Конфигурация приложения.

Все настройки читаются из переменных окружения (или .env).
Секреты (JWT_SECRET, API_KEY_PEPPER) не должны попадать в репозиторий.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Подключение к MySQL через PyMySQL
    database_url: str = "mysql+pymysql://aqua:aqua@localhost:3306/aquarium"

    # JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # API-ключи устройств: pepper добавляется к ключу перед хешированием
    api_key_pepper: str = "change-me-too"

    # Логирование
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Единственный экземпляр настроек на всё приложение
settings = Settings()