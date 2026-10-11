from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Reason, SalaryRange
from app.schemas.employer import CompanyShort


class InvitationCreate(SalaryRange):
    candidate_id: int
    vacancy_id: int | None = Field(None, description="Необязательно: можно пригласить без вакансии")
    position_title: str | None = Field(None, max_length=200, examples=["Middle Python-разработчик"],
                                       description="Необязательно: по умолчанию название вакансии или «Предложение о работе»")
    message: str = Field(min_length=3, max_length=5000, examples=["Добрый день! Мы строим платёжный сервис..."],
                         description="Описание предложения")
    contact_method: str | None = Field(None, min_length=3, max_length=255, examples=["Telegram @hr_anna"],
                                       description="Как связаться. Не передан — берём «способ связи» из профиля компании")


class InvitationAnswer(BaseModel):
    status: Literal["accepted", "rejected", "declined"] = Field(description="rejected и declined — одно и то же")
    reply: str | None = Field(None, max_length=2000)


class InvitationRespond(BaseModel):
    reply: str | None = Field(None, max_length=2000, description="Комментарий кандидата (необязательно)")


class ContactAccessIn(BaseModel):
    granted: bool = Field(description="false — закрыть контакты от этой компании, true — открыть снова")


class InvitationCandidateShort(BaseModel):
    id: int
    display_name: str
    category: str | None


class InvitationOut(BaseModel):
    id: int
    status: str = Field(description="sent | viewed | accepted | declined | withdrawn. Для UI: sent и viewed = «Ожидает ответа»")
    candidate_id: int
    employer_id: int
    position_title: str
    message: str
    salary_from: int
    salary_to: int
    salary_type: str = Field("gross", description="gross — до вычета НДФЛ, net — на руки")
    salary_type_label: str = Field("до вычета НДФЛ", examples=["до вычета НДФЛ", "на руки"])
    currency: str = "RUB"
    contacts_revoked: bool = Field(False, description="Кандидат закрыл контакты после принятия")
    contact_method: str
    vacancy_id: int | None
    company: CompanyShort
    candidate: InvitationCandidateShort
    match_score: float | None
    match_reasons: list[Reason]
    candidate_reply: str | None
    created_at: datetime
    viewed_at: datetime | None
    responded_at: datetime | None
    updated_at: datetime
