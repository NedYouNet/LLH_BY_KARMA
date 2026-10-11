"""
Зависимости FastAPI (Depends) — «кто вызывает API и что ему можно».

Пример в роутере:
    def my_invites(cand: CandidateProfile = Depends(current_candidate)): ...
FastAPI сам: достанет токен из заголовка -> проверит -> найдёт пользователя ->
проверит роль -> передаст профиль в функцию. Если что-то не так — вернёт 401/403.
"""
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import Forbidden, Unauthorized
from app.core.security import TOKEN_ACCESS, decode_token
from app.models import CandidateProfile, EmployerProfile, User
from app.repositories.repos import CandidateRepository, EmployerRepository

# tokenUrl — куда Swagger отправит логин/пароль при нажатии кнопки «Authorize»
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise Unauthorized("Требуется авторизация", "NOT_AUTHENTICATED")
    try:
        payload = decode_token(token, TOKEN_ACCESS)
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Срок действия токена истёк", "TOKEN_EXPIRED")
    except jwt.PyJWTError:
        raise Unauthorized("Неверный токен", "INVALID_TOKEN")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise Unauthorized("Пользователь не найден или заблокирован", "INVALID_TOKEN")
    return user


def current_candidate(user: User = Depends(current_user), db: Session = Depends(get_db)) -> CandidateProfile:
    if user.role != "candidate":
        raise Forbidden("Доступно только кандидатам", "ROLE_REQUIRED")
    profile = CandidateRepository(db).by_user(user.id)
    if not profile:
        raise Forbidden("Профиль кандидата не найден", "PROFILE_MISSING")
    return profile


def current_employer(user: User = Depends(current_user), db: Session = Depends(get_db)) -> EmployerProfile:
    if user.role != "employer":
        raise Forbidden("Доступно только работодателям", "ROLE_REQUIRED")
    profile = EmployerRepository(db).by_user(user.id)
    if not profile:
        raise Forbidden("Профиль работодателя не найден", "PROFILE_MISSING")
    return profile
