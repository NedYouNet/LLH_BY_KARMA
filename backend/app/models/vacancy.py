from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class Vacancy(Base):
    """Вакансия = описание потребности работодателя. По ней строится подборка кандидатов."""

    __tablename__ = "vacancies"
    __table_args__ = (
        CheckConstraint("salary_from > 0 AND salary_to >= salary_from", name="ck_vacancy_salary"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    team_description: Mapped[str | None] = mapped_column(Text, default=None)  # «чем занимается команда»
    specialization: Mapped[str] = mapped_column(String(50), index=True)
    grade: Mapped[str] = mapped_column(String(20), index=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    salary_from: Mapped[int] = mapped_column()  # ₽, обязательно по ТЗ
    salary_to: Mapped[int] = mapped_column()
    salary_type: Mapped[str] = mapped_column(String(10), default="gross")  # gross = до вычета НДФЛ, net = на руки
    work_format: Mapped[str | None] = mapped_column(String(20), default=None)
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    employer: Mapped["EmployerProfile"] = relationship()  # noqa: F821


class Application(Base):
    """Самостоятельный отклик кандидата на вакансию."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("candidate_id", "vacancy_id", name="uq_application_candidate_vacancy"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="sent", index=True)
    employer_comment: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    vacancy: Mapped["Vacancy"] = relationship()
    candidate: Mapped["CandidateProfile"] = relationship()  # noqa: F821
