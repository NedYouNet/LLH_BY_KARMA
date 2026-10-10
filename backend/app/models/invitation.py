from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedText
from app.core.database import Base, utcnow


class Invitation(Base):
    """
    Приглашение от работодателя конкретному кандидату — СМЫСЛОВОЙ ЦЕНТР продукта.

    Обязательно содержит: описание предложения, вилку ЗП (₽), компанию и способ связи.
    Вакансия — по желанию (ТЗ: «без обязательной привязки к опубликованной вакансии»).
    """

    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint("salary_from > 0 AND salary_to >= salary_from", name="ck_invitation_salary"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id", ondelete="SET NULL"), default=None)
    position_title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    salary_from: Mapped[int] = mapped_column()
    salary_to: Mapped[int] = mapped_column()
    salary_type: Mapped[str] = mapped_column(String(10), default="gross")  # gross = до вычета НДФЛ, net = на руки
    contact_method: Mapped[str] = mapped_column(EncryptedText)  # «Telegram @hr_anna» — контакт HR, шифруем
    status: Mapped[str] = mapped_column(String(20), default="sent", index=True)
    # Снимок обоснования на момент отправки — кандидат видит, почему его выбрали
    match_score: Mapped[float | None] = mapped_column(Float, default=None)
    match_reasons: Mapped[list] = mapped_column(JSON, default=list)
    candidate_reply: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    viewed_at: Mapped[datetime | None] = mapped_column(default=None)
    responded_at: Mapped[datetime | None] = mapped_column(default=None)
    # Кандидат может закрыть контакты обратно после принятия (данные, уже увиденные работодателем, не отозвать)
    contacts_revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    employer: Mapped["EmployerProfile"] = relationship()  # noqa: F821
    candidate: Mapped["CandidateProfile"] = relationship()  # noqa: F821
    vacancy: Mapped["Vacancy | None"] = relationship()  # noqa: F821


class ShortlistItem(Base):
    """«Избранное» работодателя: сохранённые кандидаты, чтобы не терять подборку при уточнении поиска."""

    __tablename__ = "shortlist_items"
    __table_args__ = (UniqueConstraint("employer_id", "candidate_id", name="uq_shortlist"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id", ondelete="SET NULL"), default=None)
    note: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ContactAccessLog(Base):
    """Журнал раскрытия контактов (152-ФЗ: кто и когда получил доступ к персональным данным)."""

    __tablename__ = "contact_access_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    basis: Mapped[str] = mapped_column(String(50))  # invitation_accepted:12 / application:7
    accessed_at: Mapped[datetime] = mapped_column(default=utcnow)
