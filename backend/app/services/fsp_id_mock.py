"""
Имитация FSP ID — сервера входа Федерации спортивного программирования на базе Keycloak.

Боевых доступов к Keycloak ФСП организаторы не дают, поэтому здесь — маленький «реалм fsp»,
который говорит на том же протоколе OpenID Connect (Authorization Code + PKCE) и по тем же
адресам, что и Keycloak:

    {issuer}/.well-known/openid-configuration   — описание провайдера (discovery)
    {issuer}/protocol/openid-connect/auth       — страница входа (почта + пароль FSP ID)
    {issuer}/protocol/openid-connect/token      — обмен одноразового кода на токены
    {issuer}/protocol/openid-connect/userinfo   — профиль участника

Наша платформа (fsp_id_client.py) работает с ним как с настоящим Keycloak. Чтобы перейти на
боевой FSP ID, достаточно FSP_ID_MODE=oidc и адреса реалма в FSP_ID_ISSUER — код платформы не меняется.

Упрощения имитации (честно описаны в документации):
  - id_token подписан HS256 общим секретом клиента (так тоже разрешает стандарт OIDC и умеет Keycloak);
    боевой Keycloak подписывает RS256, и клиент для режима oidc уже проверяет подпись по JWKS;
  - одноразовость кода контролируется в памяти процесса (в Keycloak — в его БД).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

import jwt

from app.core.config import settings

REALM_PATH = "/mock-fsp-id/realms/fsp"
CODE_TTL = 120          # секунд живёт одноразовый код
ACCESS_TTL = 300        # секунд живёт access-токен провайдера


@dataclass(frozen=True)
class FspIdAccount:
    sub: str                 # постоянный ID аккаунта в FSP ID (как sub в Keycloak)
    email: str
    name: str
    password: str
    fsp_id: str | None       # номер участника в реестре; у части аккаунтов его нет — это нормально


# Демо-аккаунты FSP ID. Пароль у всех: fsp12345
ACCOUNTS = [
    FspIdAccount("8f0e6a52-1c1d-4c7a-9a51-000000100098", "candidate@demo.ru", "Алексей Смирнов", "fsp12345", "100098"),
    FspIdAccount("8f0e6a52-1c1d-4c7a-9a51-000000100245", "maria.fsp@demo.ru", "Мария Иванова", "fsp12345", "100245"),
    FspIdAccount("8f0e6a52-1c1d-4c7a-9a51-000000100500", "olga.fsp@demo.ru", "Ольга Новикова", "fsp12345", "100500"),
    FspIdAccount("8f0e6a52-1c1d-4c7a-9a51-0000000000aa", "ivan.fsp@demo.ru", "Иван Кузнецов", "fsp12345", None),
]
_BY_EMAIL = {a.email: a for a in ACCOUNTS}
_BY_SUB = {a.sub: a for a in ACCOUNTS}
_used_codes: dict[str, float] = {}


class MockOidcError(Exception):
    def __init__(self, error: str, description: str):
        super().__init__(description)
        self.error, self.description = error, description


def issuer() -> str:
    return settings.backend_public_url.rstrip("/") + settings.api_prefix + REALM_PATH


def _key() -> str:
    """Ключ провайдера для кодов и access-токенов (свой, не совпадает с ключом платформы)."""
    return hmac.new(settings.jwt_secret.encode(), b"mock-fsp-id-provider", hashlib.sha256).hexdigest()


def discovery() -> dict:
    base = issuer() + "/protocol/openid-connect"
    return {
        "issuer": issuer(),
        "authorization_endpoint": base + "/auth",
        "token_endpoint": base + "/token",
        "userinfo_endpoint": base + "/userinfo",
        "jwks_uri": base + "/certs",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256"],
        "scopes_supported": ["openid", "email", "profile"],
        "code_challenge_methods_supported": ["S256"],
        "claims_supported": ["sub", "email", "email_verified", "name", "preferred_username", "fsp_id"],
    }


def check_client(client_id: str, redirect_uri: str) -> None:
    if client_id != settings.fsp_id_client_id:
        raise MockOidcError("unauthorized_client", "Неизвестное приложение")
    expected = settings.backend_public_url.rstrip("/") + settings.api_prefix + "/auth/fsp-id/callback"
    if redirect_uri != expected:
        raise MockOidcError("invalid_request", "redirect_uri не зарегистрирован для приложения")


def authenticate(email: str, password: str) -> FspIdAccount | None:
    acc = _BY_EMAIL.get((email or "").strip().lower())
    if acc and hmac.compare_digest(acc.password.encode(), (password or "").encode()):
        return acc
    return None


def issue_code(acc: FspIdAccount, *, client_id: str, redirect_uri: str, nonce: str | None,
               code_challenge: str) -> str:
    now = int(time.time())
    return jwt.encode({"typ": "code", "sub": acc.sub, "aud": client_id, "redirect_uri": redirect_uri,
                       "nonce": nonce, "cc": code_challenge, "jti": secrets.token_hex(8),
                       "iat": now, "exp": now + CODE_TTL}, _key(), algorithm="HS256")


def _pkce_ok(verifier: str, challenge: str) -> bool:
    digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return hmac.compare_digest(digest.encode(), (challenge or "").encode())


def exchange_code(*, code: str, client_id: str, client_secret: str, redirect_uri: str, code_verifier: str) -> dict:
    """POST /token: проверяет код, PKCE и секрет клиента, выдаёт access_token и id_token."""
    if client_id != settings.fsp_id_client_id or not hmac.compare_digest((client_secret or "").encode(),
                                                                         settings.fsp_id_client_secret.encode()):
        raise MockOidcError("invalid_client", "Неверные учётные данные клиента")
    try:
        data = jwt.decode(code, _key(), algorithms=["HS256"], audience=client_id)
    except jwt.PyJWTError:
        raise MockOidcError("invalid_grant", "Код недействителен или истёк")
    if data.get("typ") != "code" or data.get("redirect_uri") != redirect_uri:
        raise MockOidcError("invalid_grant", "Код выдан для другого адреса")
    if data["jti"] in _used_codes:
        raise MockOidcError("invalid_grant", "Код уже использован")
    if not _pkce_ok(code_verifier or "", data.get("cc")):
        raise MockOidcError("invalid_grant", "Проверка PKCE не пройдена")
    _used_codes[data["jti"]] = data["exp"]
    for jti, exp in list(_used_codes.items()):  # чистим истёкшие
        if exp < time.time():
            _used_codes.pop(jti, None)

    acc = _BY_SUB[data["sub"]]
    now = int(time.time())
    claims = userinfo_claims(acc)
    id_token = jwt.encode({"iss": issuer(), "aud": client_id, "sub": acc.sub, "iat": now, "exp": now + ACCESS_TTL,
                           "nonce": data.get("nonce"), "azp": client_id, **claims},
                          settings.fsp_id_client_secret, algorithm="HS256")
    access = jwt.encode({"iss": issuer(), "aud": "account", "sub": acc.sub, "typ": "Bearer", "iat": now,
                         "exp": now + ACCESS_TTL, "scope": "openid email profile",
                         "realm_access": {"roles": ["fsp-participant"]}}, _key(), algorithm="HS256")
    return {"access_token": access, "id_token": id_token, "token_type": "Bearer", "expires_in": ACCESS_TTL,
            "scope": "openid email profile"}


def userinfo_claims(acc: FspIdAccount) -> dict:
    out = {"sub": acc.sub, "email": acc.email, "email_verified": True, "name": acc.name,
           "preferred_username": acc.email.split("@")[0]}
    if acc.fsp_id:
        out["fsp_id"] = acc.fsp_id
    return out


def userinfo(access_token: str) -> dict:
    try:
        data = jwt.decode(access_token, _key(), algorithms=["HS256"], audience="account")
    except jwt.PyJWTError:
        raise MockOidcError("invalid_token", "Токен недействителен")
    return userinfo_claims(_BY_SUB[data["sub"]])
