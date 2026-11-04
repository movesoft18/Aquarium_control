"""
Репозиторий команд.

Только операции с БД; бизнес-логики здесь нет.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.command import Command


def create(
    db: Session,
    device_id: int,
    internal_device_id: int,
    type_: str,
    state: int,
) -> Command:
    """
    Создаёт команду со статусом pending.

    Статус по умолчанию задан в модели (server_default="pending"),
    но здесь указываем явно, чтобы не зависеть от значения в БД.
    """
    command = Command(
        device_id=device_id,
        internal_device_id=internal_device_id,
        type=type_,
        state=state,
        status="pending",
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def get_by_id(db: Session, command_id: int) -> Command | None:
    """Возвращает команду по id или None."""
    return db.query(Command).filter(Command.id == command_id).first()


def list_pending_for_device(db: Session, device_id: int) -> list[Command]:
    """
    Возвращает ожидающие команды контроллера, старые первыми.

    Сортировка по id ASC: команды выполняются в порядке создания.
    Индекс (device_id, status) ускоряет запрос.
    """
    return (
        db.query(Command)
        .filter(Command.device_id == device_id, Command.status == "pending")
        .order_by(Command.id.asc())
        .all()
    )


def mark_status(
    db: Session,
    command: Command,
    status: str,
    when: datetime,
) -> Command:
    """
    Обновляет статус команды и время выполнения.

    when заполняется при переходе в done/failed.
    """
    command.status = status
    command.executed_at = when
    db.add(command)
    db.commit()
    db.refresh(command)
    return command