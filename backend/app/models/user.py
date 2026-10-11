from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class User(Base):
    """Учётная запись. Роль определяет, какой личный кабинет доступен."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # candidate | employer | admin
    is_email_verified: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    # Задел под Keycloak / ФСП ID: сюда запишем `sub` из внешнего провайдера
    external_sub: Mapped[str | None] = mapped_column(String(255), unique=True, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)

    candidate_profile: Mapped["CandidateProfile | None"] = relationship(back_populates="user", uselist=False)  # noqa: F821
    employer_profile: Mapped["EmployerProfile | None"] = relationship(back_populates="user", uselist=False)  # noqa: F821
