# Aquarium API

Серверная часть информационной системы «Аквариум с удалённым доступом и мониторингом» (минимальная версия).

Владелец аквариума видит последнее показание температуры, управляет оборудованием (свет, аэрация) и получает подтверждение, что команда дошла до контроллера и выполнена. Контроллер имитируется эмулятором, который общается с сервером только по API.

## Стек

- Python 3.10+
- FastAPI, Uvicorn
- SQLAlchemy 2.x, Alembic
- MySQL 8.0 (PyMySQL)
- Pydantic 2.x, pydantic-settings
- passlib + bcrypt, python-jose (JWT)
- pytest, httpx
- Docker Compose (опционально)

## Возможности

- Регистрация и вход пользователя (JWT).
- Создание контроллера с API-ключом (показывается один раз).
- Приём телеметрии от контроллера по API-ключу.
- Последнее показание по контроллеру для владельца.
- Команды управления: создание, выдача контроллеру, подтверждение.
- Единый формат ответа: `{"error": 0, "message": "OK", "data": ...}`.
- Фиксированные коды ошибок (1001–1008).

## Структура

```
app/
  api/            роуты и зависимости FastAPI
  core/           конфигурация, безопасность, ответы, ошибки
  db/             Base, engine, сессии
  models/         SQLAlchemy-модели
  repositories/   доступ к данным
  schemas/        Pydantic-схемы
  services/       бизнес-логика
alembic/          миграции
emulator/         эмулятор контроллера
tests/            тесты
pyproject.toml
.env.example
docker-compose.yml
Dockerfile
```

## Быстрый старт (Docker Compose)

1. Скопировать шаблон окружения и заполнить секреты:

   ```bash
   cp .env.example .env
   ```

2. Поднять сервисы:

   ```bash
   docker compose up --build
   ```

3. Проверить healthcheck:

   ```bash
   curl http://localhost:8000/health
   ```

   Ожидаемый ответ:

   ```json
   {"error": 0, "message": "OK", "data": {"status": "healthy"}}
   ```

4. Создать пользователя и контроллер (см. раздел «Полный цикл»), подставить `AQUA_API_KEY` в `.env` и перезапустить эмулятор:

   ```bash
   docker compose up -d simulator
   ```

Остановка:

```bash
docker compose down
```

Остановка с удалением данных MySQL:

```bash
docker compose down -v
```

## Быстрый старт (без Docker)

1. Установить MySQL 8 и создать базу и пользователя:

   ```sql
   CREATE DATABASE aquarium CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'aqua'@'localhost' IDENTIFIED BY 'aqua';
   GRANT ALL PRIVILEGES ON aquarium.* TO 'aqua'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. Создать виртуальное окружение и установить зависимости:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

3. Скопировать `.env.example` в `.env` и заполнить `DATABASE_URL`, `JWT_SECRET`, `API_KEY_PEPPER`.

4. Применить миграции:

   ```bash
   alembic upgrade head
   ```

5. Запустить API:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

6. Запустить эмулятор (после создания контроллера, см. «Полный цикл»):

   ```bash
   python -m emulator.device_sim \
     --api-url http://localhost:8000/api/v1 \
     --device-id 1 \
     --api-key dk_live_...
   ```

## Переменные окружения

| Переменная | Назначение | Пример |
|---|---|---|
| `DATABASE_URL` | Строка подключения к MySQL | `mysql+pymysql://aqua:aqua@localhost:3306/aquarium` |
| `JWT_SECRET` | Секрет для подписи JWT | `change-me` |
| `JWT_ALGORITHM` | Алгоритм JWT | `HS256` |
| `JWT_EXPIRES_MINUTES` | Время жизни токена | `60` |
| `API_KEY_PEPPER` | Pepper для хеширования API-ключей | `change-me-too` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

В репозитории хранится `.env.example`. Реальный `.env` не коммитится.

## Миграции

```bash
alembic upgrade head      # применить все миграции
alembic current           # текущая ревизия
alembic revision --autogenerate -m "message"  # новая миграция по моделям
```

## Тесты

Тесты используют MySQL-базу `aquarium_test`. Она создаётся и удаляется фикстурой; схема пересоздаётся перед каждым тестом.

```bash
pytest -v
```

Требуется запущенный MySQL и права на создание и удаление базы `aquarium_test`. При необходимости задать URL тестовой базы:

```bash
export TEST_DATABASE_URL="mysql+pymysql://aqua:aqua@localhost:3306/aquarium_test"
```

## Эмулятор контроллера

Эмулятор имитирует физический контроллер аквариума: отправляет телеметрию, опрашивает команды, выполняет и подтверждает их. Общается только с API, в БД не пишет.

Внутренние устройства контроллера:

| id | Название | Тип | Поведение |
|---|---|---|---|
| 0 | Air pump | switch | включается/выключается командой |
| 1 | Light | switch | включается/выключается командой |
| 2 | Temperature sensor | sensor | только читается |

Параметры запуска:

```bash
python -m emulator.device_sim \
  --api-url http://localhost:8000/api/v1 \
  --device-id 1 \
  --api-key dk_live_... \
  --interval 10 \
  --scenario normal
```

Переменные окружения: `AQUA_API_URL`, `AQUA_DEVICE_ID`, `AQUA_API_KEY`, `AQUA_INTERVAL`, `AQUA_SCENARIO`. Сценарии: `normal`, `overheat`.

## Полный цикл

1. Зарегистрировать пользователя:

   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "secret123"}'
   ```

2. Войти и получить токен:

   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "secret123"}'
   ```

3. Создать контроллер (в ответе `data.id` и `data.api_key`):

   ```bash
   curl -X POST http://localhost:8000/api/v1/devices \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"name": "My tank"}'
   ```

4. Запустить эмулятор с `device-id` и `api-key`.

5. Проверить последнее показание:

   ```bash
   curl http://localhost:8000/api/v1/devices/1/telemetry/latest \
     -H "Authorization: Bearer <token>"
   ```

6. Создать команду:

   ```bash
   curl -X POST http://localhost:8000/api/v1/devices/1/commands \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"internal_device_id": 1, "type": "switch", "state": 1}'
   ```

Эмулятор получит команду, выполнит и подтвердит.

## API

Базовый URL: `http://localhost:8000/api/v1`. Документация: `http://localhost:8000/docs`.

| Метод | URL | Кто | Назначение |
|---|---|---|---|
| POST | `/auth/register` | — | Регистрация |
| POST | `/auth/login` | — | Вход, JWT |
| POST | `/devices` | owner | Создать контроллер |
| GET | `/devices` | owner | Список контроллеров |
| POST | `/telemetry` | device | Приём телеметрии |
| GET | `/devices/{id}/telemetry/latest` | owner | Последнее показание |
| POST | `/devices/{id}/commands` | owner | Создать команду |
| GET | `/devices/{id}/commands` | device | Ожидающие команды |
| PATCH | `/commands/{id}` | device | Подтвердить команду |

Аутентификация: JWT в заголовке `Authorization: Bearer <token>` для owner, API-ключ в заголовке `X-Device-Key: <key>` для контроллера.

## Коды ошибок

| error | HTTP | Значение |
|---|---|---|
| 0 | 200/201 | Успех |
| 1001 | 422 | Ошибка валидации |
| 1002 | 401 | Неверные учётные данные или токен |
| 1003 | 403 | Доступ запрещён |
| 1004 | 404 | Не найдено |
| 1005 | 409 | Конфликт (email занят) |
| 1006 | 401 | Неверный API-ключ устройства |
| 1007 | 422 | Недопустимая команда |
| 1008 | 500 | Внутренняя ошибка сервера |

## Типичные проблемы

| Проблема | Причина | Решение |
|---|---|---|
| `ModuleNotFoundError` при старте | неверный `WorkingDirectory` | указать каталог проекта |
| API падает при старте | MySQL не готова | дождаться готовности БД |
| 401 у эмулятора | неверный `AQUA_API_KEY` | взять реальный ключ из ответа на создание контроллера |
| Порт 8000 занят | другой процесс | сменить порт или остановить процесс |
| Миграции не применились | не выполнен `alembic upgrade head` | выполнить до запуска API |

## Лицензия

Учебный проект. Использование в курсовых и дипломных работах приветствуется.