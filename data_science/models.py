from pydantic import BaseModel, Field
from typing import Optional


class Candidate(BaseModel):
    id: int

    name: str
    email: str
    phone: str

    specialization: str
    grade: str

    skills: list[str]
    experience_years: float

    test_result: float
    is_grade_confirmed: bool = False  # <-- ДОБАВИТЬ

    fsp_id: Optional[str] = None
    fsp_achievements: int = 0

    profile_completeness: float = Field(ge=0, le=1)


class Vacancy(BaseModel):
    specialization: str
    grade: str
    required_skills: list[str]


class RankedCandidate(BaseModel):
    candidate_id: int

    score: float

    test_score: float
    fsp_score: float
    profile_score: float
    skills_score: float
    is_grade_confirmed: bool

    explanation: list[str]