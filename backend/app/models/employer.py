from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedText
from app.core.database import Base, utcnow


class EmployerProfile(Base):
    """Профиль компании-работодателя."""

    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")  # пусто, пока не заполнен профиль
    inn: Mapped[str | None] = mapped_column(String(12), default=None)  # задел под проверку через ФНС
    industry: Mapped[str | None] = mapped_column(String(50), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    # Контакты HR — тоже персональные данные конкретного человека -> шифруем
    contact_name: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    contact_email: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    contact_phone: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    contact_telegram: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    contact: Mapped[str | None] = mapped_column(EncryptedText, default=None)  # «способ связи» одной строкой, как в форме фронта
    # Уровень доверия: unverified -> inn_checked -> verified (концепция защиты от фиктивных вакансий)
    trust_level: Mapped[str] = mapped_column(String(20), default="unverified")
    # Интеграция с ATS работодателя: куда слать события (вебхук) и секрет для подписи HMAC
    ats_webhook_url: Mapped[str | None] = mapped_column(String(500), default=None)
    ats_webhook_secret: Mapped[str | None] = mapped_column(EncryptedText, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="employer_profile")  # noqa: F821


class AtsDelivery(Base):
    """Журнал отправок в ATS работодателя: что, когда и с каким результатом ушло."""

    __tablename__ = "ats_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    event: Mapped[str] = mapped_column(String(60))
    event_id: Mapped[str] = mapped_column(String(64), unique=True)  # для идемпотентности на стороне ATS
    url: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[int | None] = mapped_column(default=None)
    ok: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
