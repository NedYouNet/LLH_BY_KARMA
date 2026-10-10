"""
Подключение к базе данных через SQLAlchemy.

- engine  — «двигатель», который держит пул соединений с PostgreSQL;
- SessionLocal — фабрика сессий. Сессия = «рабочий сеанс» с БД в рамках одного запроса;
- Base — родительский класс для всех моделей (таблиц).
"""
from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def utcnow() -> datetime:
    """Текущее время в UTC (всегда храним время в UTC, а показываем фронтом в нужном поясе)."""
    return datetime.now(timezone.utc)


def _make_engine(url: str):
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        # SQLite используется только в автотестах
        kwargs["connect_args"] = {"check_same_thread": False}
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        enable_sqlite_fk(eng)
    return eng


def enable_sqlite_fk(eng) -> None:
    """В SQLite внешние ключи (и каскадное удаление) по умолчанию выключены — включаем."""
    @event.listens_for(eng, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс моделей. Все datetime-колонки — с часовым поясом."""

    type_annotation_map = {datetime: DateTime(timezone=True)}


def get_db() -> Generator[Session, None, None]:
    """
    Зависимость FastAPI: открывает сессию на время запроса и гарантированно закрывает её.
    Используется так: `def endpoint(db: Session = Depends(get_db))`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
