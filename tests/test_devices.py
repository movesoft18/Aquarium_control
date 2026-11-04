"""
Тесты устройств: создание, список, проверка прав.

Схема пересоздаётся перед каждым тестом, поэтому данные
не накапливаются между тестами.
"""

from tests.helpers import assert_error, assert_ok


def test_create_device_success(client, user_token):
    """Создание контроллера: 201, api_key есть, показывается один раз."""
    resp = client.post(
        "/api/v1/devices",
        json={"name": "My tank"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert_ok(body)
    assert body["data"]["name"] == "My tank"
    assert body["data"]["api_key"].startswith("dk_live_")
    # api_key_hash в ответ не попадает.
    assert "api_key_hash" not in body["data"]


def test_create_device_without_token(client):
    """Создание без JWT: 401, error=1002."""
    resp = client.post("/api/v1/devices", json={"name": "My tank"})
    assert resp.status_code == 401
    assert_error(resp.json(), 1002)


def test_create_device_invalid_name(client, user_token):
    """Пустое имя: 422, error=1001."""
    resp = client.post(
        "/api/v1/devices",
        json={"name": ""},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 422
    assert_error(resp.json(), 1001)


def test_list_devices_only_own(client, user_token, device):
    """
    Список контроллеров: владелец видит только свои.

    Схема чистая: у user@example.com ровно один контроллер
    из фикстуры device. Второй пользователь создаётся с другим email
    и видит пустой список.
    """
    # Первый пользователь видит свой контроллер.
    resp = client.get(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert_ok(body)
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["id"] == device["id"]

    # Второй пользователь не видит чужой контроллер.
    client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "secret123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "secret123"},
    )
    second_token = login.json()["data"]["access_token"]
    resp2 = client.get(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["data"]["items"] == []