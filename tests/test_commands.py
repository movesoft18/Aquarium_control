"""
Тесты команд: создание, выдача ожидающих, подтверждение.

Проверяются:
  - создание команды владельцем (201, error=0);
  - без JWT (1002);
  - чужой контроллер (1003);
  - sensor вместо switch (1007);
  - выдача ожидающих: успех, без ключа (1006), чужой контроллер (1003);
  - подтверждение: успех, без ключа (1006), чужая команда (1003),
    команда не найдена (1004), невалидный статус (1001).
"""

from tests.helpers import assert_error, assert_ok


def _switch_payload(internal_device_id: int = 1, state: int = 1) -> dict:
    """Тело команды switch."""
    return {
        "internal_device_id": internal_device_id,
        "type": "switch",
        "state": state,
    }


def test_create_command_success(client, device, auth_headers):
    """Создание команды: 201, error=0, status=pending."""
    resp = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert_ok(body)
    assert body["data"]["device_id"] == device["id"]
    assert body["data"]["internal_device_id"] == 1
    assert body["data"]["state"] == 1
    assert body["data"]["status"] == "pending"
    assert body["data"]["executed_at"] is None


def test_create_command_without_token(client, device):
    """Создание команды без JWT: 401, error=1002."""
    resp = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
    )
    assert resp.status_code == 401
    assert_error(resp.json(), 1002)


def test_create_command_foreign_device(client, device):
    """
    Чужой контроллер: 403, error=1003.

    Второй пользователь пытается создать команду для контроллера первого.
    """
    client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "secret123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "secret123"},
    )
    second_token = login.json()["data"]["access_token"]

    resp = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert resp.status_code == 403
    assert_error(resp.json(), 1003)


def test_create_command_sensor_not_allowed(client, device, auth_headers):
    """
    internal_device_id=2 (sensor) переключать нельзя: 422, error=1007.
    """
    resp = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(internal_device_id=2),
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert_error(resp.json(), 1007)


def test_list_pending_commands_success(client, device, auth_headers, device_headers):
    """Ожидающие команды: 200, error=0, ровно одна команда."""
    # Владелец создаёт команду.
    client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
        headers=auth_headers,
    )

    # Контроллер запрашивает ожидающие команды.
    resp = client.get(
        f"/api/v1/devices/{device['id']}/commands",
        headers=device_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert_ok(body)
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["status"] == "pending"


def test_list_pending_commands_without_key(client, device):
    """Выдача команд без X-Device-Key: 401, error=1006."""
    resp = client.get(f"/api/v1/devices/{device['id']}/commands")
    assert resp.status_code == 401
    assert_error(resp.json(), 1006)


def test_list_pending_commands_device_mismatch(client, device, device_headers):
    """
    device_id в пути не совпадает с контроллером из ключа: 403, error=1003.
    """
    resp = client.get(
        f"/api/v1/devices/{device['id'] + 999}/commands",
        headers=device_headers,
    )
    assert resp.status_code == 403
    assert_error(resp.json(), 1003)


def test_ack_command_success(client, device, auth_headers, device_headers):
    """Подтверждение команды: 200, error=0, status=done, executed_at заполнен."""
    # Владелец создаёт команду.
    create = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
        headers=auth_headers,
    )
    command_id = create.json()["data"]["id"]

    # Контроллер подтверждает выполнение.
    resp = client.patch(
        f"/api/v1/commands/{command_id}",
        json={"status": "done"},
        headers=device_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert_ok(body)
    assert body["data"]["id"] == command_id
    assert body["data"]["status"] == "done"
    assert body["data"]["executed_at"] is not None


def test_ack_command_without_key(client, device, auth_headers):
    """Подтверждение без X-Device-Key: 401, error=1006."""
    create = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
        headers=auth_headers,
    )
    command_id = create.json()["data"]["id"]

    resp = client.patch(f"/api/v1/commands/{command_id}", json={"status": "done"})
    assert resp.status_code == 401
    assert_error(resp.json(), 1006)


def test_ack_command_foreign(client, device, auth_headers, device_headers):
    """
    Чужая команда: 403, error=1003.

    Второй пользователь создаёт свой контроллер и команду;
    первый контроллер пытается подтвердить чужую команду.
    """
    # Второй пользователь и его контроллер.
    client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "secret123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "secret123"},
    )
    second_token = login.json()["data"]["access_token"]
    second_device = client.post(
        "/api/v1/devices",
        json={"name": "Second tank"},
        headers={"Authorization": f"Bearer {second_token}"},
    ).json()["data"]

    # Второй пользователь создаёт команду для своего контроллера.
    create = client.post(
        f"/api/v1/devices/{second_device['id']}/commands",
        json=_switch_payload(),
        headers={"Authorization": f"Bearer {second_token}"},
    )
    foreign_command_id = create.json()["data"]["id"]

    # Первый контроллер пытается подтвердить чужую команду.
    resp = client.patch(
        f"/api/v1/commands/{foreign_command_id}",
        json={"status": "done"},
        headers=device_headers,
    )
    assert resp.status_code == 403
    assert_error(resp.json(), 1003)


def test_ack_command_not_found(client, device, device_headers):
    """Команда не найдена: 404, error=1004."""
    resp = client.patch(
        "/api/v1/commands/999999",
        json={"status": "done"},
        headers=device_headers,
    )
    assert resp.status_code == 404
    assert_error(resp.json(), 1004)


def test_ack_command_invalid_status(client, device, auth_headers, device_headers):
    """Невалидный статус подтверждения: 422, error=1001."""
    create = client.post(
        f"/api/v1/devices/{device['id']}/commands",
        json=_switch_payload(),
        headers=auth_headers,
    )
    command_id = create.json()["data"]["id"]

    resp = client.patch(
        f"/api/v1/commands/{command_id}",
        json={"status": "unknown"},
        headers=device_headers,
    )
    assert resp.status_code == 422
    assert_error(resp.json(), 1001)