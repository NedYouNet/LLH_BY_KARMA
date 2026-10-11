from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.reference import GRADE_CODES, INDUSTRY_CODES, SPEC_CODES, WORK_FORMAT_CODES, normalize_skill
from app.schemas.common import ORMModel, Reason

Grade = Literal["intern", "junior", "middle", "senior"]
Spec = Literal["backend", "frontend", "data_science", "qa", "devops"]
WorkFormat = Literal["office", "remote", "hybrid"]


def _clean_skills(v):
    if v is None:
        return v
    out = []
    for s in v:
        n = normalize_skill(str(s))
        if n and n not in out:
            out.append(n)
    return out[:40]


class FspAchievement(BaseModel):
    event: str
    discipline: str | None = None
    level: str | None = None
    level_name: str | None = None
    year: int | None = None
    place: int | None = None
    result: str | None = None
    team: str | None = None
    source: str = Field("fsp_registry_demo", description="fsp_results_table — реальные результаты из таблицы; "
                                                         "fsp_registry_demo — демо-реестр")
    source_url: str | None = Field(None, description="Ссылка на протокол соревнования")
    verification_status: str = Field("demo", description="demo | verified. Демо-данные нельзя выдавать за проверенные")
    verified: bool = False


class Privacy(BaseModel):
    show_full_name: bool = Field(False, description="False: работодатель видит «Иван П.»")
    show_city: bool = True
    show_about: bool = True
    show_fsp_achievements: bool = True


class Consents(BaseModel):
    consent_processing: bool = Field(description="Согласие на обработку ПДн (152-ФЗ)")
    consent_publication: bool = Field(description="Согласие показывать профиль работодателям")


class CandidateProfileUpdate(BaseModel):
    """Все поля необязательны: присылайте только то, что изменилось (PATCH-семантика)."""
    full_name: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=50)
    telegram: str | None = Field(None, max_length=100)
    contact_email: EmailStr | None = None
    city: str | None = Field(None, max_length=100)
    about: str | None = Field(None, max_length=5000)
    skills: list[str] | None = None
    soft_skills: list[str] | None = None
    team_roles: list[str] | None = None
    experience_years: float | None = Field(None, ge=0, le=60)
    work_format: WorkFormat | None = None
    desired_salary_from: int | None = Field(None, gt=0, le=10_000_000)

    clean_skills = field_validator("skills")(_clean_skills)


class SurveyIn(BaseModel):
    """
    Шаг 1 обязательного пути: направление (специализация) и заявленный грейд.

    «Отрасль» из ТЗ — это IT-направление (бэкенд, фронтенд, DS…), то есть specialization.
    industry — НЕОБЯЗАТЕЛЬНАЯ предпочитаемая сфера бизнеса (финтех, ритейл…).
    """
    industry: str | None = Field(None, examples=["fintech"],
                                 description="Необязательно: предпочитаемая сфера бизнеса")
    specialization: Spec = Field(description="IT-направление — «отрасль» в терминах ТЗ")
    experience_years: float | None = Field(None, ge=0, le=60, description="Не передан — остаётся из профиля")
    skills: list[str] | None = Field(None, examples=[["Python", "FastAPI", "PostgreSQL"]],
                                     description="Не передан — берём навыки из профиля")
    team_roles: list[str] = Field(default_factory=list)
    work_format: WorkFormat | None = None
    declared_grade: Grade = Field(description="Каким грейдом кандидат себя считает (затем подтверждает тестом)")

    clean_skills = field_validator("skills")(_clean_skills)

    @field_validator("industry")
    @classmethod
    def _industry(cls, v):
        if v is not None and v not in INDUSTRY_CODES:
            raise ValueError(f"industry должен быть одним из {INDUSTRY_CODES}")
        return v


class CandidateProfileOut(ORMModel):
    """Полный профиль — видит только сам кандидат."""
    id: int
    full_name: str
    phone: str | None
    telegram: str | None
    contact_email: str | None
    city: str | None
    about: str | None
    skills: list[str]
    soft_skills: list[str]
    team_roles: list[str]
    experience_years: float
    work_format: str | None
    desired_salary_from: int | None
    industry: str | None
    declared_grade: str | None
    declared_specialization: str | None = None
    specialization: str | None
    grade: str | None
    category: str | None = None
    test_score: float | None
    skill_scores: dict
    grade_assigned_at: datetime | None
    fsp_id: str | None
    fsp_achievements: list[FspAchievement]
    fsp_score: float
    fsp_rank: str | None = None
    consent_processing: bool
    consent_publication: bool
    privacy: Privacy
    is_searchable: bool
    last_activity_at: datetime
    short_tasks_done: int
    short_tasks_avg: float | None


class ParsedResume(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    city: str | None = None
    skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    team_roles: list[str] = Field(default_factory=list)
    experience_years: float | None = None
    specialization_guess: str | None = None
    grade_guess: str | None = None
    about: str | None = None


class ResumeParseOut(BaseModel):
    source: Literal["ml", "fallback"] = Field(description="ml — разобрал ML-сервис, fallback — встроенный парсер")
    fields: ParsedResume
    applied: bool = Field(description="True — поля уже записаны в профиль (только пустые поля)")


class FspLinkIn(BaseModel):
    fsp_id: str = Field(min_length=3, max_length=50, examples=["123457"])


class GradeTarget(BaseModel):
    grade: str
    allowed: bool
    reason: str | None = None


class GradeHistoryOut(ORMModel):
    specialization: str
    old_grade: str | None
    new_grade: str
    reason: str
    changed_at: datetime


class CategoryStatus(BaseModel):
    """Текущий статус кандидата: категория, грейд, когда можно менять, история."""
    specialization: str | None
    grade: str | None
    category: str | None
    test_score: float | None
    declared_grade: str | None
    grade_assigned_at: datetime | None
    next_grade_change_at: datetime | None = Field(description="Раньше этой даты грейд не изменится")
    can_change_grade_now: bool
    survey_completed: bool
    targets: list[GradeTarget] = Field(description="На какие грейды можно пройти тест прямо сейчас")
    history: list[GradeHistoryOut]
    active_attempt_id: int | None = None


# ---------- То, что видит РАБОТОДАТЕЛЬ ----------
class CandidateContacts(BaseModel):
    full_name: str
    email: str | None
    phone: str | None
    telegram: str | None


class CandidateCard(BaseModel):
    """Карточка в выдаче. Контакты = null, пока кандидат не принял приглашение / не откликнулся."""
    id: int
    display_name: str = Field(examples=["Иван П."])
    city: str | None
    specialization: str | None
    grade: str | None = Field(description="Подтверждённый тестом грейд, а если теста ещё нет — заявленный "
                                          "кандидатом (тогда grade_verified=false)")
    category: str | None
    category_id: str | None = Field(None, description="Ключ категории: «backend:middle»", examples=["backend:middle"])
    grade_verified: bool = Field(description="Грейд подтверждён тестом (категорию ставит только сервер). "
                                             "false — кандидат виден, но ниже в выдаче")
    grade_status_label: str = Field("Подтверждён тестом", examples=["Не подтверждён: заявлен кандидатом"])
    test_score: float | None
    test_max_score: int = 100
    test_completed_at: datetime | None = Field(None, description="Когда тест подтвердил текущий грейд")
    experience_years: float
    skills: list[str]
    matched_skills: list[str] = Field(default_factory=list, description="Какие навыки из запроса есть у кандидата")
    work_format: str | None
    has_fsp: bool = Field(description="Есть достижения ФСП (одного fsp_id недостаточно)")
    fsp_id: str | None
    fsp_rank: str | None = Field(None, description="Спортивный разряд/звание: «КМС», «1 разряд»")
    fsp_verification: str = Field("none", description="none — истории нет; demo — демо-данные заглушки; verified — проверено реестром")
    match_score: float | None = Field(None, description="0..100, если карточка из подборки")
    reasons: list[Reason] = Field(default_factory=list)
    breakdown: dict | None = Field(None, description="Вклад компонент ранжирования (для «почему?»)")
    contacts_visible: bool
    contacts: CandidateContacts | None = None
    invitation_status: str | None = Field(None, description="Статус вашего приглашения этому кандидату")
    in_shortlist: bool = False


class CandidateDetail(CandidateCard):
    about: str | None
    soft_skills: list[str]
    team_roles: list[str]
    skill_scores: dict
    fsp_achievements: list[FspAchievement]
    fsp_score: float
    last_activity_at: datetime
    short_tasks_done: int
    short_tasks_avg: float | None
    contacts_hidden_reason: str | None = None


__all__ = ["Grade", "Spec", "GRADE_CODES", "SPEC_CODES", "WORK_FORMAT_CODES"]
