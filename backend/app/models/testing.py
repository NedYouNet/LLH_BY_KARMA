from datetime import datetime

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utcnow


class TestAttempt(Base):
    """
    Попытка прохождения теста.

    `items` — сгенерированные для ЭТОЙ попытки задания ВМЕСТЕ с правильными ответами.
    Правильные ответы никогда не уходят на фронтенд (см. схему AttemptItemPublic).
    """

    __tablename__ = "test_attempts"
    __test__ = False  # чтобы pytest не принимал класс за тест

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    specialization: Mapped[str] = mapped_column(String(50))
    target_grade: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    seed: Mapped[int] = mapped_column()
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id", ondelete="SET NULL"), default=None)
    items: Mapped[list] = mapped_column(JSON, default=list)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    deadline_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    score: Mapped[float | None] = mapped_column(Float, default=None)  # 0..100
    passed: Mapped[bool | None] = mapped_column(default=None)
    result: Mapped[dict] = mapped_column(JSON, default=dict)  # разбор: по навыкам, по уровням, решение по грейду


class QuestionStat(Base):
    """
    Статистика по шаблону задания: сколько раз показан, сколько раз решён верно.
    Отсюда считаем эмпирическую сложность (p-value) и дискриминативность —
    это основа «калибровки» банка заданий.
    """

    __tablename__ = "question_stats"

    template_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    shown: Mapped[int] = mapped_column(default=0)
    correct: Mapped[int] = mapped_column(default=0)
    # Сумма баллов за тест у тех, кто ответил верно/неверно — для дискриминативности
    sum_score_correct: Mapped[float] = mapped_column(Float, default=0.0)
    sum_score_wrong: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
