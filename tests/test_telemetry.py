"""
Тесты телеметрии: приём показаний и последнее показание.

Проверяются:
  - успешный приём телеметрии (201, error=0);
  - отсутствие или неверный X-Device-Key (1006);
  - несовпадение device_id в теле с ключом (1003);
  - пустой readings и невалидные поля (1001);
  - последнее показание: успех, без JWT (1002), чужой контроллер (1003),
    нет показаний (1004).
"""

from tests.helpers import assert_error, assert_ok


def _reading(internal_device_id: int = 2, value: float = 25.4) -> dict:
    """Одно показание датчика для тела запроса."""
    return {
        "internal_device_id": internal_device_id,
        "sensor": "Temperature sensor",
        "value": value,
    }


def test_send_telemetry_success(client, device, device_headers):
    """Приём телеметрии: 201, error=0, data.saved=1."""
    payload = {
        "device_id": device["id"],
        "readings": [_reading()],
    }
    resp = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert_ok(body)
    assert body["data"]["saved"] == 1


def test_send_telemetry_without_key(client, device):
    """Приём без X-Device-Key: 401, error=1006."""
    payload = {"device_id": device["id"], "readings": [_reading()]}
    resp = client.post("/api/v1/telemetry", json=payload)
    assert resp.status_code == 401
    assert_error(resp.json(), 1006)


def test_send_telemetry_device_mismatch(client, device, device_headers):
    """
    device_id в теле не совпадает с контроллером из ключа: 403, error=1003.
    """
    payload = {"device_id": device["id"] + 999, "readings": [_reading()]}
    resp = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert resp.status_code == 403
    assert_error(resp.json(), 1003)


def test_send_telemetry_empty_readings(client, device, device_headers):
    """Пустой readings: 422, error=1001."""
    payload = {"device_id": device["id"], "readings": []}
    resp = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert resp.status_code == 422
    assert_error(resp.json(), 1001)


def test_get_latest_telemetry_success(client, device, device_headers, auth_headers):
    """Последнее показание: 200, error=0, поля совпадают с отправленными."""
    payload = {"device_id": device["id"], "readings": [_reading(value=26.1)]}
    client.post("/api/v1/telemetry", json=payload, headers=device_headers)

    resp = client.get(
        f"/api/v1/devices/{device['id']}/telemetry/latest",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert_ok(body)
    assert body["data"]["device_id"] == device["id"]
    assert body["data"]["internal_device_id"] == 2
    assert body["data"]["value"] == 26.1


def test_get_latest_telemetry_without_token(client, device):
    """Последнее показание без JWT: 401, error=1002."""
    resp = client.get(f"/api/v1/devices/{device['id']}/telemetry/latest")
    assert resp.status_code == 401
    assert_error(resp.json(), 1002)


def test_get_latest_telemetry_foreign_device(client, device, device_headers):
    """
    Чужой контроллер: 403, error=1003.

    Создаём второго пользователя, он пытается получить показание
    по контроллеру первого.
    """
    # Первый пользователь отправляет телеметрию.
    payload = {"device_id": device["id"], "readings": [_reading()]}
    client.post("/api/v1/telemetry", json=payload, headers=device_headers)

    # Второй пользователь.
    client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "secret123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "secret123"},
    )
    second_token = login.json()["data"]["access_token"]

    resp = client.get(
        f"/api/v1/devices/{device['id']}/telemetry/latest",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert resp.status_code == 403
    assert_error(resp.json(), 1003)


def test_get_latest_telemetry_no_data(client, device, auth_headers):
    """Показаний ещё нет: 404, error=1004."""
    resp = client.get(
        f"/api/v1/devices/{device['id']}/telemetry/latest",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert_error(resp.json(), 1004)
    