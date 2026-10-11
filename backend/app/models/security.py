from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utcnow


class RefreshToken(Base):
    """
    Сессия пользователя = цепочка refresh-токенов (family).

    РОТАЦИЯ: при каждом обновлении старый refresh-токен «сгорает», выдаётся новый.
    ЗАЩИТА ОТ КРАЖИ: если кто-то предъявит уже сгоревший токен (значит, его украли
    и использовали дважды) — отзываем ВСЮ цепочку, оба участника будут разлогинены.
    ВЫХОД: отзываем цепочку, токен больше не обменять на новый.
    Сам токен в БД не хранится — только его идентификатор jti.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)


class AuthEvent(Base):
    """Журнал событий безопасности: входы, ошибки входа, блокировки, кражи токенов, удаления аккаунтов."""

    __tablename__ = "auth_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, default=None)
    email_hash: Mapped[str | None] = mapped_column(String(64), index=True, default=None)  # не храним сам email
    event: Mapped[str] = mapped_column(String(40), index=True)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
