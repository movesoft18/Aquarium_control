"""
Эмулятор устройства аквариума (контроллера).

Назначение
----------
Имитирует поведение физического контроллера аквариума: генерирует показания
датчиков, отправляет телеметрию на сервер по API-ключу, опрашивает ожидающие
команды и подтверждает их выполнение.

Важно: эмулятор НЕ пишет в базу данных напрямую. Он общается только с API
сервера. Вся бизнес-логика (валидация, сохранение, проверка прав) — на сервере.

Модель внутренних устройств
---------------------------
devices_data — словарь внутренних устройств контроллера:
  - тип "switch": можно включать/выключать командой, состояние — status (0/1)
  - тип "sensor": только читается, status — текущее значение

Поток работы
------------
1. Сгенерировать показания для всех sensor-устройств.
2. Отправить телеметрию: POST /telemetry.
3. Раз в полинтервала опросить команды: GET /devices/{id}/commands?status=pending.
4. Для каждой команды: применить и подтвердить через PATCH /commands/{id}.
5. Подождать до следующей итерации.

Запуск
------
    python device_sim.py --api-url http://localhost:8000/api/v1 \
        --device-id 10 --api-key <ключ> --interval 10

Переменные окружения
--------------------
    AQUA_API_URL, AQUA_DEVICE_ID, AQUA_API_KEY, AQUA_INTERVAL, AQUA_SCENARIO
"""

import argparse
import json
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Модель внутренних устройств контроллера.
#
# Ключ словаря — internal_device_id (целое число).
# Значение — описание устройства:
#   name   — человекочитаемое имя (используется в поле sensor телеметрии);
#   type   — "switch" (управляемое) или "sensor" (только чтение);
#   status — для switch: 0/1 (текущее состояние);
#            для sensor: текущее значение (начальное).
#
# Список фиксирован для минимальной версии. Добавление нового устройства —
# новая запись с уникальным id; API и сервер при этом не меняются, потому
# что в телеметрии передаётся internal_device_id.
# ---------------------------------------------------------------------------
devices_data = {
    0: {
        "name": "Air pump",
        "type": "switch",
        "status": 1,
    },
    1: {
        "name": "Light",
        "type": "switch",
        "status": 0,
    },
    2: {
        "name": "Temperature sensor",
        "type": "sensor",
        "status": 22,
    },
}


# Логгер модуля. Настраивается в run() в зависимости от --verbose.
log = logging.getLogger("device_sim")


# ---------------------------------------------------------------------------
# Генерация показаний датчиков.
#
# Класс отвечает только за sensor-устройства. Switch-устройства сюда не
# попадают: их состояние меняется командами, а не генерацией.
# ---------------------------------------------------------------------------
class SensorState:
    """
    Хранит «внутреннее» состояние датчиков и генерирует правдоподобные
    значения: плавный дрейф + небольшой шум.

    Начальные значения берутся из devices_data (поле status у sensor).
    """

    def __init__(self):
        # Текущие значения только для sensor-устройств: {internal_device_id: value}
        self._values: dict[int, float] = {
            dev_id: float(dev["status"])
            for dev_id, dev in devices_data.items()
            if dev["type"] == "sensor"
        }
        # Активный сценарий (None — normal). Нужен для проверки уведомлений.
        self._scenario: str | None = None
        # Время старта сценария, чтобы отсчитывать «через 20 секунд».
        self._scenario_started_at: float | None = None

    def set_scenario(self, name: str) -> None:
        """Включает сценарий (например, overheat) и запоминает время старта."""
        self._scenario = name
        self._scenario_started_at = time.time()
        log.info("Сценарий включён: %s", name)

    def _drift(self, value: float, step: float, low: float, high: float) -> float:
        """
        Плавное изменение значения: случайный шаг в пределах ±step,
        с ограничением диапазоном [low, high].
        """
        value += random.uniform(-step, step)
        return max(low, min(high, value))

    def read(self) -> list[dict[str, Any]]:
        """
        Возвращает список показаний для всех sensor-устройств:
            [{"internal_device_id": 2, "sensor": "Temperature sensor", "value": 22.4}]

        Формат соответствует спецификации API:
        readings[] с полями internal_device_id, sensor, value.
        """
        readings: list[dict[str, Any]] = []

        for dev_id, dev in devices_data.items():
            # Switch-устройства не дают показаний — пропускаем.
            if dev["type"] != "sensor":
                continue

            value = self._values.get(dev_id, float(dev["status"]))

            # Для температурного датчика — плавный дрейф в диапазоне 22..28 °C.
            if dev["name"] == "Temperature sensor":
                value = self._drift(value, 0.1, 22.0, 28.0)

                # Сценарий «перегрев»: через 20 секунд температура уходит
                # за верхнюю границу (около 30 °C). Нужен для проверки
                # правил уведомлений в будущих итерациях.
                if self._scenario == "overheat" and self._scenario_started_at is not None:
                    elapsed = time.time() - self._scenario_started_at
                    if elapsed > 20:
                        value = 30.0 + random.uniform(-0.3, 0.3)

            self._values[dev_id] = value
            readings.append(
                {
                    "internal_device_id": dev_id,
                    "sensor": dev["name"],
                    "value": round(value, 2),
                }
            )

        return readings


# ---------------------------------------------------------------------------
# Клиент API сервера.
#
# Тонкая обёртка над requests: отправка телеметрии, получение команд,
# подтверждение выполнения. Все ответы разбираются по соглашению
# о формате ответа API: {"error": 0, "message": "OK", "data": ...}.
# ---------------------------------------------------------------------------
class ApiClient:
    def __init__(self, base_url: str, device_id: int, api_key: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.api_key = api_key
        self.timeout = timeout
        # Сессия requests с общими заголовками: ключ устройства и JSON.
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Device-Key": self.api_key,
                "Content-Type": "application/json",
            }
        )

    def _parse(self, resp: requests.Response) -> dict[str, Any] | None:
        """
        Разбирает тело ответа как JSON. Если тело не JSON —
        логирует предупреждение и возвращает None.
        """
        try:
            return resp.json()
        except ValueError:
            log.warning("Ответ не является JSON: %s", resp.text[:200])
            return None

    def send_telemetry(self, readings: list[dict[str, Any]]) -> bool:
        """
        Отправляет телеметрию: POST /telemetry.

        Тело запроса:
            {
              "device_id": 10,
              "recorded_at": "2025-03-15T10:40:00Z",
              "readings": [
                {"internal_device_id": 2, "sensor": "Temperature sensor", "value": 25.4}
              ]
            }

        Возвращает True, если сервер ответил error == 0.
        """
        # Если датчиков нет — отправлять нечего, считаем успехом.
        if not readings:
            log.debug("Нет показаний для отправки (нет sensor-устройств)")
            return True

        payload = {
            "device_id": self.device_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "readings": readings,
        }
        url = f"{self.base_url}/telemetry"
        try:
            resp = self.session.post(url, data=json.dumps(payload), timeout=self.timeout)
        except requests.RequestException as exc:
            # Сетевая ошибка: API недоступно, таймаут, обрыв и т.п.
            # Не падаем — логируем и продолжаем цикл.
            log.warning("Не удалось отправить телеметрию: %s", exc)
            return False

        body = self._parse(resp)
        if body is None:
            return False

        # Успех по соглашению: error == 0.
        if body.get("error") == 0:
            log.info("Телеметрия отправлена: %s", readings)
            return True

        # Обработка типовых ошибок по кодам.
        error = body.get("error")
        message = body.get("message")
        if error == 1006:
            # Неверный API-ключ устройства: повторять бессмысленно.
            log.error("Неверный API-ключ устройства: %s", message)
        elif error == 1001:
            # Ошибка валидации: детали лежат в data.fields.
            fields = (body.get("data") or {}).get("fields", {})
            log.warning("Ошибка валидации телеметрии: %s %s", message, fields)
        else:
            log.warning("Сервер отклонил телеметрию: error=%s message=%s", error, message)
        return False

    def fetch_pending_commands(self) -> list[dict[str, Any]]:
        """
        Запрашивает ожидающие команды: GET /devices/{id}/commands?status=pending.

        По соглашению список лежит в data.items.
        Возвращает список команд (возможно, пустой).
        """
        url = f"{self.base_url}/devices/{self.device_id}/commands"
        try:
            resp = self.session.get(url, params={"status": "pending"}, timeout=self.timeout)
        except requests.RequestException as exc:
            log.warning("Не удалось получить команды: %s", exc)
            return []

        body = self._parse(resp)
        if body is None:
            return []

        if body.get("error") != 0:
            log.warning(
                "Сервер вернул ошибку при запросе команд: error=%s message=%s",
                body.get("error"), body.get("message"),
            )
            return []

        data = body.get("data") or {}
        items = data.get("items", [])
        return items if isinstance(items, list) else []

    def ack_command(self, command_id: int, status: str, result: dict[str, Any] | None = None) -> bool:
        """
        Подтверждает выполнение команды: PATCH /commands/{id}.

        Тело запроса: {"status": "done"} или {"status": "failed"}.
        Возвращает True, если сервер ответил error == 0.
        """
        url = f"{self.base_url}/commands/{command_id}"
        payload = {"status": status}
        if result:
            payload["result"] = result
        try:
            resp = self.session.patch(url, data=json.dumps(payload), timeout=self.timeout)
        except requests.RequestException as exc:
            log.warning("Не удалось подтвердить команду %s: %s", command_id, exc)
            return False

        body = self._parse(resp)
        if body is None:
            return False

        if body.get("error") == 0:
            log.info("Команда %s подтверждена: %s", command_id, status)
            return True

        log.warning(
            "Сервер отклонил подтверждение команды %s: error=%s message=%s",
            command_id, body.get("error"), body.get("message"),
        )
        return False


# ---------------------------------------------------------------------------
# Применение команды к внутреннему состоянию устройств.
#
# В минимальной версии поддерживается только type == "switch".
# Возвращает кортеж (успех, результат), где результат — словарь для
# подтверждения или описание ошибки.
# ---------------------------------------------------------------------------
def apply_command(command: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    cmd_type = command.get("type")
    payload = command.get("payload") or {}

    if cmd_type == "switch":
        device_id = payload.get("device_id")
        state = payload.get("state")

        # Проверка: устройство существует.
        if device_id not in devices_data:
            return False, {"error": f"device {device_id} not found"}

        device = devices_data[device_id]

        # Проверка: устройство — switch (датчик переключать нельзя).
        if device["type"] != "switch":
            return False, {"error": f"device {device_id} is not a switch"}

        # Проверка: допустимое состояние.
        if state not in (0, 1):
            return False, {"error": "state must be 0 or 1"}

        # Применяем: меняем состояние внутреннего устройства.
        device["status"] = state
        log.info("Устройство %s (%s) переключено в %s", device_id, device["name"], state)
        return True, {"device_id": device_id, "status": state}

    # Неизвестный тип команды: в минимальной версии не поддерживается.
    return False, {"error": f"unknown command type: {cmd_type}"}


# ---------------------------------------------------------------------------
# Основной цикл.
#
# Флаг _running управляет циклом и сбрасывается по SIGINT/SIGTERM,
# чтобы завершение было корректным (не обрывалось посреди запроса).
# ---------------------------------------------------------------------------
_running = True


def _handle_signal(signum, frame):
    """Обработчик сигналов: аккуратно останавливает основной цикл."""
    global _running
    log.info("Получен сигнал %s, завершаемся", signum)
    _running = False


def run(args: argparse.Namespace) -> int:
    """
    Основной цикл эмулятора:
      1. сгенерировать показания;
      2. отправить телеметрию;
      3. периодически опросить команды и подтвердить их;
      4. подождать до следующей итерации.
    """
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )

    # Корректное завершение по Ctrl+C и SIGTERM.
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = ApiClient(args.api_url, args.device_id, args.api_key)
    sensors = SensorState()

    if args.scenario:
        sensors.set_scenario(args.scenario)

    log.info(
        "Эмулятор запущен: api=%s device_id=%s interval=%ss scenario=%s",
        args.api_url, args.device_id, args.interval, args.scenario or "normal",
    )

    # Опрос команд — раз в полинтервала, но не чаще, чем раз в 2 секунды.
    last_command_poll = 0.0
    command_poll_interval = max(2.0, args.interval / 2)

    while _running:
        # 1. Показания sensor-устройств.
        readings = sensors.read()

        # 2. Отправка телеметрии (ошибки логируются внутри клиента).
        client.send_telemetry(readings)

        # 3. Опрос и выполнение команд.
        now = time.time()
        if now - last_command_poll >= command_poll_interval:
            last_command_poll = now
            for command in client.fetch_pending_commands():
                command_id = command.get("id")
                ok, result = apply_command(command)
                status = "done" if ok else "failed"
                client.ack_command(command_id, status, result)

        # 4. Ожидание до следующей итерации с реакцией на сигнал завершения.
        deadline = time.time() + args.interval
        while _running and time.time() < deadline:
            time.sleep(0.5)

    log.info("Эмулятор остановлен")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Разбор аргументов командной строки. Значения по умолчанию берутся
    из переменных окружения, чтобы эмулятор было удобно запускать
    в контейнере или systemd-юните.
    """
    parser = argparse.ArgumentParser(description="Эмулятор устройства аквариума")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("AQUA_API_URL", "http://localhost:8000/api/v1"),
        help="Базовый URL API сервера",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=int(os.environ.get("AQUA_DEVICE_ID", "1")),
        help="ID контроллера в системе",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("AQUA_API_KEY", ""),
        help="API-ключ устройства",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("AQUA_INTERVAL", "10")),
        help="Интервал отправки телеметрии, секунды",
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "overheat"],
        default=os.environ.get("AQUA_SCENARIO", "normal"),
        help="Сценарий работы эмулятора",
    )
    parser.add_argument("--verbose", action="store_true", help="Подробный лог")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Точка входа: проверяет наличие API-ключа и запускает цикл."""
    args = parse_args(argv or sys.argv[1:])
    if not args.api_key:
        print("Ошибка: не задан API-ключ устройства (--api-key или AQUA_API_KEY)", file=sys.stderr)
        return 2
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())