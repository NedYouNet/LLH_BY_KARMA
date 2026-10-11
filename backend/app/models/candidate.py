from datetime import datetime

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedText
from app.core.database import Base, utcnow

DEFAULT_PRIVACY = {
    "show_full_name": False,   # False -> работодатель видит «Иван П.»
    "show_city": True,
    "show_about": True,
    "show_fsp_achievements": True,
}


class CandidateProfile(Base):
    """
    Профиль соискателя.

    Важно: поля specialization + grade (= КАТЕГОРИЯ) заполняет ТОЛЬКО система
    по итогам тестирования. Сам кандидат указывает лишь заявку: declared_specialization
    и declared_grade («на что претендую»).

    Пока тест не пройден, кандидат НЕ скрыт: работодатель видит его с пометкой
    «грейд не подтверждён», ниже в выдаче (рекомендация организаторов: не выкидывать
    кандидата из оборота). Подтверждённая категория всегда важнее заявленной.
    """

    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # --- Личные данные и контакты (СКРЫТЫ от работодателя до принятия инвайта/отклика) ---
    # EncryptedText: в БД лежит шифротекст AES-256-GCM, в коде — обычная строка (app/core/crypto.py)
    full_name: Mapped[str] = mapped_column(EncryptedText, default="")
    phone: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    telegram: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    contact_email: Mapped[str | None] = mapped_column(EncryptedText, default=None)

    # --- Резюме ---
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    about: Mapped[str | None] = mapped_column(Text, default=None)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    team_roles: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    work_format: Mapped[str | None] = mapped_column(String(20), default=None)
    desired_salary_from: Mapped[int | None] = mapped_column(default=None)
    resume_text: Mapped[str | None] = mapped_column(EncryptedText, default=None)  # текст из PDF: в нём ПДн -> шифруем

    # --- Опрос и категория ---
    industry: Mapped[str | None] = mapped_column(String(50), default=None)
    survey: Mapped[dict] = mapped_column(JSON, default=dict)
    declared_grade: Mapped[str | None] = mapped_column(String(20), default=None)
    declared_specialization: Mapped[str | None] = mapped_column(String(50), index=True, default=None)
    specialization: Mapped[str | None] = mapped_column(String(50), index=True, default=None)
    grade: Mapped[str | None] = mapped_column(String(20), index=True, default=None)
    test_score: Mapped[float | None] = mapped_column(Float, default=None)  # 0..100, последний зачтённый
    skill_scores: Mapped[dict] = mapped_column(JSON, default=dict)  # {"SQL": 0.8, ...} по итогам теста
    grade_assigned_at: Mapped[datetime | None] = mapped_column(default=None)
    grade_changed_at: Mapped[datetime | None] = mapped_column(default=None)

    # --- ФСП ---
    fsp_id: Mapped[str | None] = mapped_column(String(50), unique=True, default=None)
    fsp_achievements: Mapped[list] = mapped_column(JSON, default=list)
    fsp_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1, сила подтверждённых достижений
    fsp_rank: Mapped[str | None] = mapped_column(String(30), default=None)  # спортивный разряд: «КМС», «1 разряд»
    fsp_synced_at: Mapped[datetime | None] = mapped_column(default=None)

    # --- 152-ФЗ: согласия и приватность ---
    consent_processing: Mapped[bool] = mapped_column(default=False)   # согласие на обработку ПДн
    consent_publication: Mapped[bool] = mapped_column(default=False)  # согласие показывать профиль работодателям
    consent_at: Mapped[datetime | None] = mapped_column(default=None)
    privacy: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_PRIVACY))

    # --- Активность (свежесть профиля) ---
    last_activity_at: Mapped[datetime] = mapped_column(default=utcnow)
    short_tasks_done: Mapped[int] = mapped_column(default=0)
    short_tasks_avg: Mapped[float | None] = mapped_column(Float, default=None)  # средняя оценка 0..10

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="candidate_profile")  # noqa: F821

    # --- Категория для выдачи: подтверждённая тестом, а если теста ещё нет — заявленная ---
    @property
    def grade_verified(self) -> bool:
        return bool(self.grade and self.specialization)

    @property
    def effective_specialization(self) -> str | None:
        return self.specialization if self.grade_verified else self.declared_specialization

    @property
    def effective_grade(self) -> str | None:
        return self.grade if self.grade_verified else self.declared_grade

    @property
    def is_searchable(self) -> bool:
        """Попадает ли кандидат в выдачу: есть согласия и категория (подтверждённая или заявленная)."""
        return bool(self.consent_publication and self.consent_processing
                    and self.effective_grade and self.effective_specialization)


class GradeHistory(Base):
    """История смены грейда — нужна для правила «не чаще раза в 90 дней» и для показа кандидату."""

    __tablename__ = "grade_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    specialization: Mapped[str] = mapped_column(String(50))
    old_grade: Mapped[str | None] = mapped_column(String(20), default=None)
    new_grade: Mapped[str] = mapped_column(String(20))
    attempt_id: Mapped[int | None] = mapped_column(ForeignKey("test_attempts.id", ondelete="SET NULL"), default=None)
    reason: Mapped[str] = mapped_column(String(200), default="")
    changed_at: Mapped[datetime] = mapped_column(default=utcnow)
