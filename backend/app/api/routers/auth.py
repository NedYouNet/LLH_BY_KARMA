from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import AppError, errors
from app.core.rate_limit import client_ip
from app.models import User
from app.repositories.repos import CandidateRepository, EmployerRepository
from app.schemas.auth import (
    LoginRequest, LogoutRequest, MeOut, RefreshRequest, RegisterRequest, RegisterResponse, ResendVerificationRequest, TokenPair,
    UserOut, VerifyEmailRequest,
)
from app.schemas.common import Message
from app.services.auth_service import AuthService
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/auth", tags=["Авторизация"])


def auth_service(request: Request, db: Session = Depends(get_db)) -> AuthService:
    """Сервис авторизации со знанием IP и браузера клиента (для лимитов и журнала безопасности)."""
    return AuthService(db, ip=client_ip(request), user_agent=request.headers.get("user-agent"))


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED,
             responses=errors(409, 429), summary="Регистрация кандидата или работодателя")
def register(data: RegisterRequest, svc: AuthService = Depends(auth_service)):
    """Создаёт пользователя и пустой профиль нужной роли, отправляет письмо для подтверждения email."""
    return svc.register(data)


@router.post("/verify-email", response_model=UserOut, responses=errors(401), summary="Подтвердить email (токен из письма)")
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    return AuthService(db).verify_email(data.token)


@router.get("/verify-email", response_class=HTMLResponse, include_in_schema=False)
def verify_email_link(token: str, db: Session = Depends(get_db)):
    """Сюда ведёт ссылка из письма: подтверждаем и показываем простую страницу со ссылкой на вход."""
    try:
        AuthService(db).verify_email(token)
        text = "Email подтверждён! Теперь можно войти."
    except AppError as e:
        text = e.detail
    return f"<html><body style='font-family:sans-serif;padding:40px'><h2>{text}</h2>" \
           f"<a href='{settings.frontend_url}/login'>Перейти ко входу</a></body></html>"


@router.post("/resend-verification", response_model=Message, summary="Отправить письмо подтверждения ещё раз")
def resend(data: ResendVerificationRequest, svc: AuthService = Depends(auth_service)):
    svc.resend_verification(data.email)
    return Message(message="Если такой email зарегистрирован и не подтверждён — письмо отправлено")


@router.post("/login", response_model=TokenPair, responses=errors(401, 403, 429), summary="Вход (JSON) — для фронтенда")
def login(data: LoginRequest, svc: AuthService = Depends(auth_service)):
    """После 5 неудачных попыток подряд вход по этому email блокируется на 15 минут (429)."""
    return svc.login(data.email, data.password)


@router.post("/token", response_model=TokenPair, responses=errors(401, 403, 429),
             summary="Вход через форму — для кнопки Authorize в Swagger (username = email)")
def login_form(form: OAuth2PasswordRequestForm = Depends(), svc: AuthService = Depends(auth_service)):
    return svc.login(form.username, form.password)


@router.post("/refresh", response_model=TokenPair, responses=errors(401), summary="Обновить пару токенов (ротация)")
def refresh(data: RefreshRequest, svc: AuthService = Depends(auth_service)):
    """
    Старый refresh-токен «сгорает», выдаётся новая пара — сохраните ОБА новых токена.
    Повторное использование сгоревшего токена = признак кражи -> вся сессия отзывается (401 TOKEN_REUSED).
    """
    return svc.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Выход (отзыв сессии)")
def logout(data: LogoutRequest | None = None, user: User = Depends(current_user),
           svc: AuthService = Depends(auth_service)):
    """
    С `refresh_token` — завершает эту сессию; без тела — выход на всех устройствах.
    После выхода refresh-токен больше не обменять. Фронт удаляет оба токена у себя.
    """
    svc.logout(user, data.refresh_token if data else None)


@router.get("/me", response_model=MeOut, responses=errors(401), summary="Кто я + чек-лист онбординга")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = MeOut(user=UserOut.model_validate(user))
    if user.role == "candidate":
        c = CandidateRepository(db).by_user(user.id)
        out.candidate_profile_id = c.id
        out.onboarding = CandidateService.onboarding(c)
    elif user.role == "employer":
        e = EmployerRepository(db).by_user(user.id)
        out.employer_profile_id = e.id
        out.onboarding = {"company_filled": bool(e.description and e.industry)}
    return out
