"""
Репозиторий контроллеров.

Только операции с БД; бизнес-логики здесь нет.
"""

from sqlalchemy.orm import Session

from app.models.device import Device
from datetime import datetime


def touch_last_seen(db: Session, device: Device, when: datetime) -> None:
    """
    Обновляет last_seen_at контроллера.

    Вызывается после успешного сохранения телеметрии.
    Коммит делает вызывающий код (сервис), чтобы объединить
    сохранение показаний и обновление устройства в одну транзакцию.
    """
    device.last_seen_at = when
    db.add(device)

def get_by_id(db: Session, device_id: int) -> Device | None:
    """Возвращает контроллер по id или None."""
    return db.query(Device).filter(Device.id == device_id).first()


def get_by_api_key_hash(db: Session, api_key_hash: str) -> Device | None:
    """
    Возвращает контроллер по хешу API-ключа или None.
    Используется в get_current_device.
    """
    return db.query(Device).filter(Device.api_key_hash == api_key_hash).first()


def list_by_owner(db: Session, owner_id: int) -> list[Device]:
    """Возвращает все контроллеры владельца, упорядоченные по id."""
    return (
        db.query(Device)
        .filter(Device.owner_id == owner_id)
        .order_by(Device.id)
        .all()
    )


def create(
    db: Session,
    owner_id: int,
    name: str,
    api_key_hash: str,
) -> Device:
    """
    Создаёт контроллер и возвращает его.

    api_key_hash - хеш ключа; сам ключ в БД не хранится.
    """
    device = Device(owner_id=owner_id, name=name, api_key_hash=api_key_hash)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device