from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.candidate import CandidateCard, Grade, Spec, WorkFormat, _clean_skills


class SearchIn(BaseModel):
    """
    Запрос подборки. Фронтенд хранит этот объект и при уточнении фильтров
    просто меняет поля и шлёт снова — подборка не теряется (а избранное — в /shortlist).
    """
    specialization: Spec | None = None
    grades: list[Grade] = Field(default_factory=list, description="Пусто = все грейды")
    skills: list[str] = Field(default_factory=list, examples=[["Python", "PostgreSQL", "Docker"]])
    text: str | None = Field(None, max_length=5000, description="Описание потребности свободным текстом")
    fsp_only: bool = Field(False, description="Только с подтверждёнными достижениями ФСП")
    only_verified: bool = Field(False, description="Только с грейдом, подтверждённым тестом "
                                                   "(по умолчанию кандидаты без теста тоже видны, но ниже)")
    min_test_score: float | None = Field(None, ge=0, le=100)
    work_format: WorkFormat | None = None
    city: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class CategoryBucket(BaseModel):
    """Блок категории в выдаче: «Бэкенд · Middle — 34 кандидата (30 подтверждены тестом)»."""
    specialization: str
    grade: str
    category: str
    count: int = Field(description="Всего в категории")
    verified: int = Field(description="Из них грейд подтверждён тестом")
    unverified: int = Field(description="Из них грейд только заявлен (тест не пройден) — показываются ниже")
    with_fsp: int
    avg_test_score: float = Field(description="Средний балл теста у подтверждённых")


class SearchOut(BaseModel):
    total: int
    page: int
    size: int
    categories: list[CategoryBucket]
    items: list[CandidateCard]


class ShortlistIn(BaseModel):
    candidate_id: int
    vacancy_id: int | None = None
    note: str | None = Field(None, max_length=500)


class ShortlistOut(BaseModel):
    id: int
    note: str | None
    vacancy_id: int | None
    created_at: datetime
    candidate: CandidateCard


class NeedIn(BaseModel):
    """Потребность работодателя: кого ищем."""
    title: str | None = Field(None, max_length=200, examples=["Бэкендер в платёжную команду"])
    specialization: Spec
    grade: Grade
    stack: list[str] = Field(default_factory=list, examples=[["Python", "PostgreSQL", "Docker"]])
    description: str | None = Field(None, max_length=5000, description="Чем занимается команда, задачи")

    clean_stack = field_validator("stack")(_clean_skills)


class NeedOut(NeedIn):
    id: int
    created_at: datetime
    updated_at: datetime
