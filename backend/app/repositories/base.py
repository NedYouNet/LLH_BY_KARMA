"""
Репозитории — единственное место, где пишутся запросы к БД.

Слои приложения (сверху вниз):
  Router (HTTP: принять запрос, вернуть ответ)
    -> Service (бизнес-правила: «нельзя менять грейд чаще раза в 90 дней»)
      -> Repository (SQL-запросы: «найди кандидатов категории X»)

Зачем так сложно? Каждый слой можно менять и тестировать отдельно:
поменяли PostgreSQL на другую БД — правим только репозитории.
"""
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base

M = TypeVar("M", bound=Base)


class BaseRepository(Generic[M]):
    model: type[M]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id_: int) -> M | None:
        return self.db.get(self.model, id_)

    def add(self, obj: M) -> M:
        self.db.add(obj)
        self.db.flush()  # получаем id, но транзакцию ещё не фиксируем
        return obj

    def delete(self, obj: M) -> None:
        self.db.delete(obj)

    def count(self, *where) -> int:
        return self.db.scalar(select(func.count()).select_from(self.model).where(*where)) or 0
