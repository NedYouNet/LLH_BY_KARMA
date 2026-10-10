from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.candidate import Grade, Spec


class StartAttemptIn(BaseModel):
    specialization: Spec
    target_grade: Grade = Field(description="На какой грейд проходим тест")
    vacancy_id: int | None = Field(None, description="Если тест строится под вакансию — задания подбираются по её стеку")


class CodeSpec(BaseModel):
    function_name: str
    signature: str
    examples: list[dict] = Field(description="Видимые примеры: [{args: [...], expected: ...}] — можно гонять в Pyodide")
    language: str = "python"
    starter_code: str = Field(description="Что положить в редактор Monaco изначально")


class AttemptItemPublic(BaseModel):
    """Задание БЕЗ правильного ответа."""
    id: str = Field(examples=["q1"])
    level: int = Field(description="0=Intern … 3=Senior")
    skill: str
    kind: str = Field(description="single — выбрать вариант, input — ввести ответ, code — написать функцию")
    text: str
    options: list[str] | None = None
    code: CodeSpec | None = None


class AttemptOut(BaseModel):
    id: int
    specialization: str
    target_grade: str
    status: str
    started_at: datetime
    deadline_at: datetime
    seconds_left: int
    items: list[AttemptItemPublic]
    score: float | None = Field(None, description="Заполнено после сдачи")
    max_score: int = 100
    passed: bool | None = None
    finished_at: datetime | None = None


class SubmitIn(BaseModel):
    answers: dict[str, str] = Field(
        description="id задания -> ответ. Для single — текст варианта, для code — исходный код",
        examples=[{"q1": "201", "q2": "def solve(nums):\n    return 0"}])


class ItemResult(BaseModel):
    id: str
    skill: str
    level: int
    score: float
    status: str = Field(description="correct | wrong | partial | no_answer")
    passed: int | None = None
    total: int | None = None
    violations: list[str] | None = None


class GradeDecision(BaseModel):
    grade_before: str | None
    grade_after: str | None
    changed: bool
    message: str
    upgrade_suggested: bool = False
    next_change_at: datetime | None = None


class AttemptResultOut(BaseModel):
    id: int
    status: str
    score: float
    passed: bool
    specialization: str
    target_grade: str
    decision: GradeDecision
    by_skill: dict[str, float]
    by_level: dict[str, float]
    items: list[ItemResult]
    finished_at: datetime | None


class AttemptSummary(BaseModel):
    id: int
    specialization: str
    target_grade: str
    status: str
    score: float | None
    passed: bool | None
    started_at: datetime
    finished_at: datetime | None


class AssessmentPreview(BaseModel):
    """Как система сформирует тест под вакансию (для демонстрации механики жюри)."""
    vacancy_id: int
    specialization: str
    grade: str
    blueprint: dict[str, int] = Field(description="Сколько заданий каждого уровня")
    skills_focus: list[str]
    sample_variants: list[list[AttemptItemPublic]] = Field(description="Два варианта для двух разных кандидатов")
