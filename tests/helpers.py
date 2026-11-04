"""
Вспомогательные функции для проверки ответов API.

Соглашение о формате ответа:
    {"error": 0, "message": "OK", "data": ...}
"""


def assert_api_response(body: dict) -> None:
    """Проверяет, что тело ответа соответствует соглашению."""
    assert set(body.keys()) == {"error", "message", "data"}
    assert isinstance(body["error"], int)
    assert isinstance(body["message"], str)


def assert_ok(body: dict, expected_error: int = 0) -> None:
    """Проверяет успешный ответ."""
    assert_api_response(body)
    assert body["error"] == expected_error


def assert_error(body: dict, expected_error: int) -> None:
    """Проверяет ответ с ошибкой."""
    assert_api_response(body)
    assert body["error"] == expected_error