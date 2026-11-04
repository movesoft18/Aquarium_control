"""
Тесты аутентификации: регистрация и вход.

Схема пересоздаётся перед каждым тестом, поэтому email
user@example.com не конфликтует между тестами.
"""

from tests.helpers import assert_error, assert_ok


def test_register_success(client):
    """Регистрация нового пользователя: 201, error=0, data.id есть."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert_ok(body)
    assert body["data"]["email"] == "user@example.com"
    assert "id" in body["data"]
    # Пароль в ответ не попадает.
    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]


def test_register_duplicate_email(client):
    """Повторная регистрация с тем же email: 409, error=1005."""
    payload = {"email": "dup@example.com", "password": "secret123"}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert_error(resp.json(), 1005)


def test_register_validation_error(client):
    """Короткий пароль и неверный email: 422, error=1001, data.fields."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "123"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert_error(body, 1001)
    # Детали валидации лежат в data.fields.
    assert "fields" in body["data"]
    assert len(body["data"]["fields"]) >= 1


def test_login_success(client):
    """Успешный вход: 200, error=0, есть access_token."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "secret123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert_ok(body)
    assert body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Неверный пароль: 401, error=1002."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "secret123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "another123"},
    )
    assert resp.status_code == 401
    assert_error(resp.json(), 1002)