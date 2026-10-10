from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class ShortTask(Base):
    """Короткое задание от работодателя: «реши» или «предложи подход». Поддерживает свежесть профиля."""

    __tablename__ = "short_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), default="approach")  # solution | approach
    specialization: Mapped[str] = mapped_column(String(50), index=True)
    grade: Mapped[str | None] = mapped_column(String(20), default=None)  # None = для всех грейдов
    deadline_at: Mapped[datetime | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    employer: Mapped["EmployerProfile"] = relationship()  # noqa: F821


class ShortTaskSubmission(Base):
    __tablename__ = "short_task_submissions"
    __table_args__ = (UniqueConstraint("task_id", "candidate_id", name="uq_short_task_submission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("short_tasks.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    employer_score: Mapped[float | None] = mapped_column(Float, default=None)  # 0..10
    employer_feedback: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)

    task: Mapped["ShortTask"] = relationship()
