"""
Репозиторий телеметрии.

Только операции с БД; бизнес-логики здесь нет.
"""

from sqlalchemy.orm import Session

from app.models.telemetry import Telemetry


def create_many(db: Session, records: list[Telemetry]) -> int:
    """
    Сохраняет список показаний одной транзакцией.

    Возвращает количество сохранённых записей.
    """
    db.add_all(records)
    db.commit()
    return len(records)


def get_latest_by_device(db: Session, device_id: int) -> Telemetry | None:
    """
    Возвращает последнее показание по контроллеру или None.

    Сортировка по recorded_at DESC, затем по id DESC:
    если два показания пришли в одну секунду, побеждает более позднее
    по id. Индекс (device_id, recorded_at) ускоряет запрос.
    """
    return (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.recorded_at.desc(), Telemetry.id.desc())
        .first()
    )