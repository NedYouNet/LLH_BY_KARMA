"""
Вход через FSP ID: наша платформа — «клиент» (Relying Party) OpenID Connect.

Поток Authorization Code + PKCE (так же подключаются к Keycloak):

  1. GET /api/auth/fsp-id/login      -> переадресация на страницу входа FSP ID.
     Состояние (state) — подписанный нами короткоживущий токен: в нём одноразовый nonce,
     секрет PKCE (code_verifier) и куда вернуть пользователя. Хранить сессию на сервере не нужно.
  2. Пользователь вводит почту и пароль FSP ID на стороне ФСП (пароль ФСП к нам не попадает).
  3. GET /api/auth/fsp-id/callback   <- FSP ID возвращает одноразовый code.
     Мы обмениваем code на токены (с code_verifier и секретом клиента), проверяем id_token
     (подпись, издатель, аудитория, срок, nonce) и берём профиль из userinfo.
  4. Находим или создаём пользователя по `sub` (users.external_sub); если в профиле FSP ID есть номер
     участника — сразу подтягиваем достижения из реестра ФСП.
  5. Выдаём обычные токены платформы.

Режимы (FSP_ID_MODE): mock — встроенная имитация реалма ФСП (fsp_id_mock.py), вызывается напрямую;
oidc — настоящий Keycloak по HTTP: discovery, обмен кода, проверка id_token по JWKS (RS256).
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import settings
from app.core.errors import AppError, BadRequest
from app.services import fsp_id_mock

STATE_TTL = 600


class FspIdError(AppError):
    status_code = 400
    code = "FSP_ID_ERROR"


def enabled() -> bool:
    return settings.fsp_id_mode in ("mock", "oidc")


def redirect_uri() -> str:
    return settings.backend_public_url.rstrip("/") + settings.api_prefix + "/auth/fsp-id/callback"


_discovery_cache: dict | None = None


def provider() -> dict:
    """Описание провайдера: адреса входа, обмена кода, профиля и ключей."""
    global _discovery_cache
    if settings.fsp_id_mode == "mock":
        return fsp_id_mock.discovery()
    if _discovery_cache is None:
        url = settings.fsp_id_issuer.rstrip("/") + "/.well-known/openid-configuration"
        _discovery_cache = httpx.get(url, timeout=10).raise_for_status().json()
    return _discovery_cache


def _state_key() -> str:
    return settings.jwt_secret + ":fsp-id-state"


def build_login_url(return_to: str) -> str:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    nonce = secrets.token_urlsafe(16)
    now = int(time.time())
    state = jwt.encode({"typ": "fsp_id_state", "cv": verifier, "nonce": nonce, "ret": return_to,
                        "iat": now, "exp": now + STATE_TTL}, _state_key(), algorithm="HS256")
    params = {"response_type": "code", "client_id": settings.fsp_id_client_id, "redirect_uri": redirect_uri(),
              "scope": "openid email profile", "state": state, "nonce": nonce,
              "code_challenge": challenge, "code_challenge_method": "S256"}
    return provider()["authorization_endpoint"] + "?" + urlencode(params)


def read_state(state: str) -> dict:
    try:
        data = jwt.decode(state, _state_key(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise FspIdError("Вход через FSP ID занял слишком много времени — начните заново", "FSP_ID_STATE_EXPIRED")
    except jwt.PyJWTError:
        raise FspIdError("Некорректный ответ FSP ID (state)", "FSP_ID_STATE_INVALID")
    if data.get("typ") != "fsp_id_state":
        raise FspIdError("Некорректный ответ FSP ID (state)", "FSP_ID_STATE_INVALID")
    return data


def _exchange(code: str, verifier: str) -> dict:
    if settings.fsp_id_mode == "mock":
        try:
            return fsp_id_mock.exchange_code(code=code, client_id=settings.fsp_id_client_id,
                                             client_secret=settings.fsp_id_client_secret,
                                             redirect_uri=redirect_uri(), code_verifier=verifier)
        except fsp_id_mock.MockOidcError as e:
            raise FspIdError(f"FSP ID отклонил вход: {e.description}", "FSP_ID_EXCHANGE_FAILED")
    r = httpx.post(provider()["token_endpoint"], timeout=10, data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(),
        "client_id": settings.fsp_id_client_id, "client_secret": settings.fsp_id_client_secret,
        "code_verifier": verifier})
    if r.status_code != 200:
        raise FspIdError("FSP ID отклонил вход", "FSP_ID_EXCHANGE_FAILED")
    return r.json()


def _verify_id_token(id_token: str, nonce: str) -> dict:
    p = provider()
    try:
        if settings.fsp_id_mode == "mock":
            claims = jwt.decode(id_token, settings.fsp_id_client_secret, algorithms=["HS256"],
                                audience=settings.fsp_id_client_id, issuer=p["issuer"])
        else:
            key = jwt.PyJWKClient(p["jwks_uri"]).get_signing_key_from_jwt(id_token).key
            claims = jwt.decode(id_token, key, algorithms=["RS256", "ES256"], audience=settings.fsp_id_client_id,
                                issuer=p["issuer"])
    except jwt.PyJWTError as e:
        raise FspIdError(f"Подпись FSP ID не прошла проверку: {e}", "FSP_ID_TOKEN_INVALID")
    if claims.get("nonce") != nonce:
        raise FspIdError("Ответ FSP ID не относится к этому входу (nonce)", "FSP_ID_TOKEN_INVALID")
    return claims


def _userinfo(access_token: str) -> dict:
    if settings.fsp_id_mode == "mock":
        return fsp_id_mock.userinfo(access_token)
    r = httpx.get(provider()["userinfo_endpoint"], timeout=10, headers={"Authorization": f"Bearer {access_token}"})
    if r.status_code != 200:
        raise FspIdError("Не удалось получить профиль FSP ID", "FSP_ID_USERINFO_FAILED")
    return r.json()


def complete_login(code: str, state: dict) -> dict:
    """Шаги 3–4: проверенный профиль участника FSP ID {sub, email, email_verified, name, fsp_id?}."""
    if not code:
        raise BadRequest("FSP ID не вернул код авторизации", "FSP_ID_ERROR")
    tokens = _exchange(code, state["cv"])
    id_claims = _verify_id_token(tokens.get("id_token", ""), state["nonce"])
    info = _userinfo(tokens["access_token"])
    if info.get("sub") != id_claims.get("sub"):
        raise FspIdError("Профиль FSP ID не совпадает с токеном", "FSP_ID_TOKEN_INVALID")
    return {**id_claims, **info}
