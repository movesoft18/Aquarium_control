# Базовый образ Python 3.11 (совместим с requires-python >= 3.10).
FROM python:3.11-slim

# Рабочая директория внутри контейнера.
WORKDIR /app

# Системные зависимости для сборки пакетов и для mysql-клиента.
# curl нужен для healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Сначала копируем только файлы зависимостей:
# слой с зависимостями кэшируется, пока не изменится pyproject.toml.
COPY pyproject.toml ./
COPY app ./app
COPY emulator ./emulator
COPY alembic.ini ./
COPY alembic ./alembic
COPY .env ./

# Устанавливаем проект и зависимости.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Точка входа по умолчанию - API.
# Эмулятор запускается с другой командой (см. docker-compose.yml).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]