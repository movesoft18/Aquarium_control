"""
Роуты аутентификации: регистрация и вход.

Роуты тонкие: валидируют вход через Pydantic, вызывают сервис,
формируют ответ через ok().
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenData, UserData
from app.services import auth as auth_service
from app.schemas.common import ApiResponse, ErrorResponse, ValidationErrorResponse


router = APIRouter()


@router.post(
    "/register",
    status_code=201,
    response_model=ApiResponse[UserData],
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    """
    Регистрация пользователя.

    Ответ: data = user.serialize (без password_hash).
    Ошибки: 1001 (422) при невалидных данных, 1005 (409) если email занят.
    """
    user = auth_service.register(db, payload.email, payload.password)
    return ok(user.serialize)


@router.post(
    "/login",
    response_model=ApiResponse[TokenData],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """
    Вход.

    Ответ: data.access_token - JWT, data.token_type = "bearer".
    Ошибки: 1001 (422), 1002 (401) при неверных данных.
    """
    token = auth_service.login(db, payload.email, payload.password)
    return ok({"access_token": token, "token_type": "bearer"})