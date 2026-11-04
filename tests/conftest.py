"""
Общие фикстуры для тестов на MySQL.

- test_engine: движок тестовой БД aquarium_test (создаётся один раз).
- db_session: сессия с пересозданием схемы перед каждым тестом.
- client: TestClient с подменённой зависимостью get_db.
- user_token: JWT зарегистрированного пользователя.
- device: созданный контроллер с api_key.

Изоляция тестов: перед каждым тестом схема пересоздаётся
(drop_all + create_all). Это откатывает всё, что закоммитили роуты,
и следующий тест стартует с чистой БД.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists, drop_database

from app.db.base import Base
from app.db.session import get_db
from app.main import app


# URL тестовой БД. Можно переопределить через переменную окружения.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/aquarium_test",
)


@pytest.fixture(scope="session")
def test_engine():
    """
    Движок тестовой БД на всю сессию тестов.

    Перед тестами БД создаётся (если её нет), после - удаляется.
    Схема пересоздаётся в db_session перед каждым тестом.
    """
    # Создаём БД, если её ещё нет.
    if not database_exists(TEST_DATABASE_URL):
        create_database(TEST_DATABASE_URL)

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    yield engine

    # После всех тестов: закрываем соединения и удаляем БД.
    engine.dispose()
    if database_exists(TEST_DATABASE_URL):
        drop_database(TEST_DATABASE_URL)


@pytest.fixture()
def db_session(test_engine):
    """
    Сессия БД для одного теста с чистой схемой.

    Перед тестом: drop_all + create_all. Это удаляет данные,
    закоммиченные предыдущими тестами, и гарантирует изоляцию.
    После теста сессия просто закрывается: откатывать нечего,
    схема будет пересоздана перед следующим тестом.
    """
    # Чистая схема перед каждым тестом.
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    """
    TestClient с подменённой зависимостью get_db.

    Роуты получают тестовую сессию вместо рабочей.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def user_token(client) -> str:
    """
    Регистрирует пользователя user@example.com и возвращает JWT.

    Схема перед тестом чистая, поэтому email не конфликтует
    с другими тестами.
    """
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret123"},
    )
    return resp.json()["data"]["access_token"]


@pytest.fixture()
def device(client, user_token) -> dict:
    """
    Создаёт контроллер для текущего пользователя.

    Возвращает данные: {"id": ..., "api_key": ..., "name": ...}.
    """
    resp = client.post(
        "/api/v1/devices",
        json={"name": "My tank"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return resp.json()["data"]

@pytest.fixture()
def auth_headers(user_token) -> dict:
    """
    Заголовки для запросов владельца.

    Возвращает {"Authorization": "Bearer "}.
    """
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture()
def device_headers(device) -> dict:
    """
    Заголовки для запросов контроллера.

    Возвращает {"X-Device-Key": "<api_key>"}.
    """
    return {"X-Device-Key": device["api_key"]}