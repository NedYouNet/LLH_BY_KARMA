from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.candidate import CandidateCard, Grade, Spec, WorkFormat, _clean_skills
from app.schemas.common import SalaryRange
from app.schemas.employer import CompanyShort


class VacancyCreate(SalaryRange):
    title: str = Field(min_length=3, max_length=200, examples=["Python-разработчик в платёжную команду"])
    description: str = Field(min_length=10, max_length=10000)
    team_description: str | None = Field(None, max_length=5000, description="Чем занимается команда")
    specialization: Spec
    grade: Grade
    skills: list[str] = Field(default_factory=list, examples=[["Python", "FastAPI", "PostgreSQL", "Kafka"]])
    work_format: WorkFormat | None = None
    city: str | None = None

    clean_skills = field_validator("skills")(_clean_skills)


class VacancyUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, min_length=10, max_length=10000)
    team_description: str | None = None
    specialization: Spec | None = None
    grade: Grade | None = None
    skills: list[str] | None = None
    salary_from: int | None = Field(None, gt=0, le=10_000_000)
    salary_to: int | None = Field(None, gt=0, le=10_000_000)
    salary_type: Literal["gross", "net"] | None = None
    work_format: WorkFormat | None = None
    city: str | None = None
    status: Literal["active", "closed"] | None = None

    clean_skills = field_validator("skills")(_clean_skills)

    @model_validator(mode="after")
    def check_range(self):
        if self.salary_from and self.salary_to and self.salary_to < self.salary_from:
            raise ValueError("salary_to должна быть не меньше salary_from")
        return self


class VacancyOut(BaseModel):
    id: int
    title: str
    description: str
    team_description: str | None
    specialization: str
    grade: str
    category: str | None
    skills: list[str]
    salary_from: int
    salary_to: int
    salary_type: str = Field("gross", description="gross — до вычета НДФЛ, net — на руки")
    salary_type_label: str = Field("до вычета НДФЛ", examples=["до вычета НДФЛ", "на руки"])
    currency: str = "RUB"
    work_format: str | None
    city: str | None
    status: str
    company: CompanyShort
    created_at: datetime
    updated_at: datetime
    applications_count: int | None = Field(None, description="Только для владельца вакансии")
    my_application_status: str | None = Field(None, description="Только для кандидата: статус его отклика")


class ApplicationCreate(BaseModel):
    cover_letter: str | None = Field(None, max_length=5000)


class ApplicationStatusUpdate(BaseModel):
    status: Literal["viewed", "accepted", "rejected"]
    comment: str | None = Field(None, max_length=2000)


class ApplicationOut(BaseModel):
    id: int
    status: str = Field(description="sent | viewed | accepted | rejected | withdrawn")
    cover_letter: str | None
    employer_comment: str | None
    created_at: datetime
    updated_at: datetime
    vacancy: VacancyOut
    candidate: CandidateCard | None = Field(None, description="Заполняется для работодателя")
