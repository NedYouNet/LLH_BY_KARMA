from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class EmployerProfileUpdate(BaseModel):
    company_name: str | None = Field(None, max_length=200)
    inn: str | None = Field(None, pattern=r"^\d{10}(\d{2})?$", description="ИНН: 10 или 12 цифр")
    industry: str | None = None
    description: str | None = Field(None, max_length=5000)
    website: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    contact_name: str | None = Field(None, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(None, max_length=50)
    contact_telegram: str | None = Field(None, max_length=100)
    contact: str | None = Field(None, max_length=255, description="Способ связи одной строкой: почта, телефон или Telegram")


class EmployerProfileOut(ORMModel):
    """Профиль компании. Пока company_name пустое, приглашать кандидатов нельзя (400 COMPANY_PROFILE_INCOMPLETE)."""
    id: int
    company_name: str
    inn: str | None
    industry: str | None
    description: str | None
    website: str | None
    city: str | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    contact_telegram: str | None
    contact: str | None
    trust_level: str
    created_at: datetime


class CompanyShort(BaseModel):
    """То, что кандидат видит о компании в приглашении/вакансии."""
    id: int
    company_name: str
    industry: str | None = None
    website: str | None = None
    city: str | None = None
    trust_level: str = "unverified"


class AtsConfigIn(BaseModel):
    webhook_url: str = Field(max_length=500, examples=["https://ats.example.ru/hooks/fsp-talent"],
                             description="Куда платформа будет отправлять события (вебхук вашей ATS)")
    rotate_secret: bool = Field(False, description="Выдать новый секрет подписи (старый перестанет работать)")


class AtsDeliveryOut(ORMModel):
    id: int
    event: str
    event_id: str
    status_code: int | None
    ok: bool
    error: str | None
    created_at: datetime


class AtsConfigOut(BaseModel):
    enabled: bool
    webhook_url: str | None
    events: list[str] = Field(description="Какие события отправляются")
    secret: str | None = Field(None, description="Секрет подписи. Показывается ОДИН раз — при создании/смене")
    secret_hint: str | None = Field(None, examples=["…x9Qa"])
    signature_header: str
    recent_deliveries: list[AtsDeliveryOut]


class MockAtsEventOut(BaseModel):
    id: int
    event: str = Field(examples=["invitation.accepted"])
    event_id: str
    signature_valid: bool = Field(description="Подпись X-FSP-Signature проверена секретом компании")
    received_at: datetime
    payload: dict | None = Field(None, description="Тело события, как его получила бы ATS (с контактами кандидата)")


class MockAtsReceipt(BaseModel):
    received: bool
    duplicate: bool = Field(description="True — это событие уже приходило (повтор не создаёт дубль)")
    event_id: str
    signature_valid: bool
