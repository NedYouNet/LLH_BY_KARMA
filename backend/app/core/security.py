"""
Безопасность: хеширование паролей и JWT-токены.

Пароли НИКОГДА не храним в открытом виде. Мы используем scrypt из стандартной
библиотеки Python: это «медленная» функция с солью — даже при утечке базы
подобрать пароль очень дорого. Внешних зависимостей не нужно.

JWT — подписанный «пропуск». Сервер выдаёт его при входе, фронтенд кладёт его
в заголовок `Authorization: Bearer <токен>` при каждом запросе. Подделать токен
нельзя без секретного ключа. Структура полей (claims) сделана похожей на Keycloak
(`sub`, `email`, `realm_access.roles`), чтобы потом безболезненно перейти на ФСП ID.
"""
import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

import jwt

from app.core.config import settings
from app.core.database import utcnow

# Параметры scrypt (рекомендации OWASP: N=2^14..2^17, r=8, p=1)
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return hmac.compare_digest(actual, expected)  # сравнение за постоянное время


# Типы токенов: доступ, обновление, подтверждение почты
TOKEN_ACCESS = "access"
TOKEN_REFRESH = "refresh"
TOKEN_EMAIL = "email_verify"


def create_token(*, user_id: int, email: str, role: str, token_type: str, expires: timedelta,
                 jti: str | None = None, family: str | None = None) -> str:
    now = utcnow()
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "email": email,
        "typ": token_type,
        "realm_access": {"roles": [role]},  # как в Keycloak
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": jti or secrets.token_hex(16),
    }
    if family:
        payload["fam"] = family  # идентификатор сессии (цепочки refresh-токенов)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, email: str, role: str) -> str:
    return create_token(user_id=user_id, email=email, role=role, token_type=TOKEN_ACCESS,
                        expires=timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user_id: int, email: str, role: str, jti: str, family: str) -> str:
    return create_token(user_id=user_id, email=email, role=role, token_type=TOKEN_REFRESH,
                        expires=timedelta(days=settings.refresh_token_days), jti=jti, family=family)


def create_email_token(user_id: int, email: str, role: str) -> str:
    return create_token(user_id=user_id, email=email, role=role, token_type=TOKEN_EMAIL,
                        expires=timedelta(hours=settings.email_token_hours))


def decode_token(token: str, expected_type: str, verify_exp: bool = True) -> dict[str, Any]:
    """Проверяет подпись, срок жизни и тип токена. Бросает jwt.PyJWTError при проблеме."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], issuer=settings.jwt_issuer,
                         options={"verify_exp": verify_exp})
    if payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


# ----------------------------- политика паролей -----------------------------
COMMON_PASSWORDS = {"password", "password1", "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop",
                    "11111111", "00000000", "iloveyou", "admin123", "password123", "qwerty12", "1q2w3e4r",
                    "1q2w3e4r5t", "zaq12wsx", "abc12345", "parol123", "privet123", "йцукенгш"}


def password_problems(password: str, email: str | None = None) -> list[str]:
    """Проверка стойкости пароля (рекомендации NIST SP 800-63B: длина + запрет словарных паролей)."""
    problems = []
    if len(password) < 8:
        problems.append("не короче 8 символов")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        problems.append("должен содержать буквы и цифры")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("слишком распространённый пароль")
    if email and len(email.split("@")[0]) >= 4 and email.split("@")[0].lower() in password.lower():
        problems.append("не должен содержать ваш email")
    return problems


def email_fingerprint(email: str) -> str:
    """HMAC от email: позволяет считать неудачные входы по email, не храня сам email в журнале."""
    return hmac.new(settings.jwt_secret.encode(), email.strip().lower().encode(), hashlib.sha256).hexdigest()
