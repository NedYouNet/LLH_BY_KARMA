from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.candidate import CandidateCard, Grade, Spec
from app.schemas.employer import CompanyShort


class ShortTaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200, examples=["Как бы вы спроектировали rate limiter?"])
    description: str = Field(min_length=10, max_length=10000)
    kind: Literal["solution", "approach"] = Field("approach", description="solution — решить, approach — предложить подход")
    specialization: Spec
    grade: Grade | None = Field(None, description="None — для всех грейдов специализации")
    deadline_at: datetime | None = None


class ShortTaskOut(BaseModel):
    id: int
    title: str
    description: str
    kind: str
    specialization: str
    grade: str | None
    deadline_at: datetime | None
    is_active: bool
    created_at: datetime
    company: CompanyShort
    submissions_count: int | None = None
    my_submission_status: str | None = None


class SubmissionCreate(BaseModel):
    answer: str = Field(min_length=5, max_length=20000)


class SubmissionReview(BaseModel):
    score: float = Field(ge=0, le=10, description="Оценка 0..10 — влияет на «свежесть» профиля в ранжировании")
    feedback: str | None = Field(None, max_length=2000)


class SubmissionOut(BaseModel):
    id: int
    task_id: int
    answer: str
    status: str
    employer_score: float | None
    employer_feedback: str | None
    created_at: datetime
    reviewed_at: datetime | None
    candidate: CandidateCard | None = None
