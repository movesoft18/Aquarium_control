"""
Репозиторий пользователей.

Только операции с БД; бизнес-логики здесь нет.
"""

from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    """Возвращает пользователя по id или None."""
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> User | None:
    """Возвращает пользователя по email или None."""
    return db.query(User).filter(User.email == email).first()


def create(db: Session, email: str, password_hash: str) -> User:
    """
    Создаёт пользователя и возвращает его.

    Пароль уже должен быть хеширован вызывающим кодом.
    """
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user