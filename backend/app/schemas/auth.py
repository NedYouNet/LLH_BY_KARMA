from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

from app.core.security import password_problems

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr = Field(examples=["ivan@example.ru"])
    password: str = Field(min_length=8, max_length=128, examples=["StrongPass123"])
    role: Literal["candidate", "employer"] = Field(description="Какой кабинет создать")
    full_name: str | None = Field(default=None, max_length=200, description="Для кандидата (можно позже)")
    company_name: str | None = Field(default=None, max_length=200,
                                     description="Для работодателя: можно сразу или позже в профиле компании")
    consent_processing: bool = Field(False, description="Галочка «Даю согласие на обработку ПДн» на форме регистрации")

    @field_validator("password")
    @classmethod
    def strong_password(cls, v, info):
        # field_validator -> ошибка 422 придёт в fields.password, фронт подсветит именно это поле
        problems = password_problems(v, info.data.get("email"))
        if problems:
            raise PydanticCustomError("weak_password", "Пароль: " + "; ".join(problems))
        return v



class RegisterResponse(BaseModel):
    user_id: int
    email: EmailStr
    role: str
    verification_required: bool
    message: str
    dev_verification_token: str | None = Field(
        default=None, description="Только в режиме dev: токен подтверждения, чтобы не ходить в почту на демо")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Через сколько секунд истечёт access_token")
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(None, description="Завершить эту сессию. Без токена — выйти на всех устройствах")


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class UserOut(ORMModel):
    id: int
    email: EmailStr
    role: str
    is_email_verified: bool
    created_at: datetime


class MeOut(BaseModel):
    user: UserOut
    candidate_profile_id: int | None = None
    employer_profile_id: int | None = None
    onboarding: dict = Field(default_factory=dict, description="Что ещё не сделано: для подсказок в UI")
