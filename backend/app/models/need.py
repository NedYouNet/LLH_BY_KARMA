from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utcnow


class EmployerNeed(Base):
    """
    Потребность работодателя («кого ищем»): специализация, грейд, стек, описание.
    Это не публичная вакансия — по ней строится подборка (GET /api/candidates?needs_id=...).
    Сохраняется в БД, поэтому после перезагрузки страницы требования не теряются.
    """

    __tablename__ = "employer_needs"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    specialization: Mapped[str] = mapped_column(String(50))
    grade: Mapped[str] = mapped_column(String(20))
    stack: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
