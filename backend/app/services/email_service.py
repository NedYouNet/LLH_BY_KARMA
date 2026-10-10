"""
Отправка писем.

- Если SMTP_HOST не задан — письмо просто печатается в лог (удобно, пока нет почты).
- В docker-compose поднят Mailpit: все письма видно в браузере на http://localhost:8025
  (настоящие письма никуда не уходят — идеально для демо).
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("email")


def send_email(to: str, subject: str, text: str) -> None:
    if not settings.smtp_host:
        log.warning("EMAIL (SMTP не настроен) -> %s | %s\n%s", to, subject, text)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(text)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password or "")
            smtp.send_message(msg)
    except OSError:
        log.exception("Не удалось отправить письмо на %s", to)


def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.backend_public_url}{settings.api_prefix}/auth/verify-email?token={token}"
    send_email(to, "Подтвердите email — FSP Talent",
               f"Здравствуйте!\n\nДля завершения регистрации перейдите по ссылке:\n{link}\n\n"
               f"Ссылка действует {settings.email_token_hours} ч. Если вы не регистрировались — игнорируйте письмо.")


def send_invitation_email(to: str, company: str, position: str, salary_from: int, salary_to: int,
                          salary_type: str = "gross") -> None:
    kind = "на руки" if salary_type == "net" else "до вычета НДФЛ"
    send_email(to, f"Новое приглашение от {company}",
               f"{company} приглашает вас на позицию «{position}».\n"
               f"Зарплата: {salary_from:,} – {salary_to:,} ₽ ({kind}).\n\n"
               f"Откройте личный кабинет, чтобы принять или отклонить: {settings.frontend_url}/candidate/invitations"
               .replace(",", " "))
