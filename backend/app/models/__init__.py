"""
Модели = таблицы базы данных, описанные классами Python (ORM SQLAlchemy).

Одна модель = одна таблица, один атрибут = одна колонка.
Alembic смотрит на эти классы и сам генерирует SQL-миграции.

Импортируем все модели здесь, чтобы Alembic и приложение «видели» их все.
"""
from app.models.enums import ApplicationStatus, AttemptStatus, InvitationStatus, Role, SubmissionStatus, VacancyStatus
from app.models.user import User
from app.models.candidate import CandidateProfile, GradeHistory
from app.models.employer import AtsDelivery, EmployerProfile
from app.models.vacancy import Application, Vacancy
from app.models.testing import QuestionStat, TestAttempt
from app.models.invitation import ContactAccessLog, Invitation, ShortlistItem
from app.models.short_task import ShortTask, ShortTaskSubmission
from app.models.need import EmployerNeed
from app.models.security import AuthEvent, RefreshToken

__all__ = [
    "Role", "InvitationStatus", "ApplicationStatus", "AttemptStatus", "VacancyStatus", "SubmissionStatus",
    "User", "CandidateProfile", "GradeHistory", "EmployerProfile", "Vacancy", "Application",
    "TestAttempt", "QuestionStat", "Invitation", "ShortlistItem", "ContactAccessLog",
    "ShortTask", "ShortTaskSubmission", "EmployerNeed", "RefreshToken", "AuthEvent", "AtsDelivery",
]
