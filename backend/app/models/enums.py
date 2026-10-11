"""
Перечисления (статусы и роли).

Храним их в БД как обычные строки (а не как ENUM PostgreSQL) — так проще
добавлять новые значения без сложных миграций.
"""
from enum import StrEnum


class Role(StrEnum):
    candidate = "candidate"
    employer = "employer"
    admin = "admin"


class InvitationStatus(StrEnum):
    """Жизненный цикл приглашения (главная механика ТЗ)."""
    sent = "sent"            # работодатель отправил
    viewed = "viewed"        # кандидат открыл
    accepted = "accepted"    # кандидат принял -> контакты раскрываются
    declined = "declined"    # кандидат отклонил
    withdrawn = "withdrawn"  # работодатель отозвал


class ApplicationStatus(StrEnum):
    """Жизненный цикл отклика кандидата на вакансию (доп. сценарий)."""
    sent = "sent"
    viewed = "viewed"
    accepted = "accepted"    # работодатель готов общаться
    rejected = "rejected"
    withdrawn = "withdrawn"  # кандидат отозвал


class AttemptStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"
    expired = "expired"


class VacancyStatus(StrEnum):
    active = "active"
    closed = "closed"


class SubmissionStatus(StrEnum):
    submitted = "submitted"
    reviewed = "reviewed"
