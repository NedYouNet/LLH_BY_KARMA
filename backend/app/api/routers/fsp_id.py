"""
Вход через FSP ID (OpenID Connect) + встроенная имитация FSP ID на базе протокола Keycloak.

Для платформы:      GET /api/auth/fsp-id/config | /login | /callback
Имитация Keycloak:  /api/mock-fsp-id/realms/fsp/...   (работает при FSP_ID_MODE=mock)
"""
import html
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import AppError, NotFound
from app.schemas.auth import TokenPair
from app.services import fsp_id_client, fsp_id_mock
from app.api.routers.auth import auth_service
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth/fsp-id", tags=["Авторизация"])
mock_router = APIRouter(prefix=fsp_id_mock.REALM_PATH, tags=["FSP ID (имитация Keycloak)"])

ReturnTo = Literal["frontend", "json"]


class FspIdConfig(BaseModel):
    enabled: bool
    mode: str
    login_url: str | None
    provider_name: str = "FSP ID"
    demo_accounts: list[dict] | None = None


class FspIdLoginResult(TokenPair):
    created: bool
    linked_existing: bool
    fsp_linked: bool


# ============================================================= для платформы
@router.get("/config", response_model=FspIdConfig, summary="Показывать ли кнопку «Войти через FSP ID»")
def config():
    if not fsp_id_client.enabled():
        return FspIdConfig(enabled=False, mode=settings.fsp_id_mode, login_url=None)
    demo = None
    if settings.fsp_id_mode == "mock":
        demo = [{"email": a.email, "password": a.password, "name": a.name, "fsp_id": a.fsp_id}
                for a in fsp_id_mock.ACCOUNTS]
    return FspIdConfig(enabled=True, mode=settings.fsp_id_mode,
                       login_url=f"{settings.api_prefix}/auth/fsp-id/login", demo_accounts=demo)


@router.get("/login", status_code=302, summary="Начать вход через FSP ID (переадресация на страницу FSP ID)",
            response_class=RedirectResponse)
def login(return_to: ReturnTo = Query("frontend", description="frontend — вернуть на сайт с токенами; "
                                                                "json — показать токены (удобно из Swagger)")):
    """
    Открывайте этот адрес в браузере (не через fetch): пользователь уйдёт на страницу входа FSP ID и вернётся.
    Для проверки без фронтенда: `/api/auth/fsp-id/login?return_to=json`.
    """
    if not fsp_id_client.enabled():
        raise NotFound("Вход через FSP ID отключён", "FSP_ID_DISABLED")
    return RedirectResponse(fsp_id_client.build_login_url(return_to), status_code=302)


def _to_frontend(fragment: dict) -> RedirectResponse:
    # Токены — во фрагменте (#...): он не уходит на серверы и не попадает в их журналы
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/fsp-id#{urlencode(fragment)}", status_code=302)


@router.get("/callback", summary="Сюда FSP ID возвращает пользователя после входа",
            responses={200: {"model": FspIdLoginResult}, 302: {"description": "Возврат на фронтенд с токенами"}})
def callback(code: str | None = None, state: str | None = None, error: str | None = None,
             error_description: str | None = None, svc: AuthService = Depends(auth_service)):
    try:
        st = fsp_id_client.read_state(state or "")
    except AppError as e:
        return JSONResponse(status_code=400, content={"code": e.code, "message": e.detail, "detail": e.detail})
    try:
        if error:
            raise fsp_id_client.FspIdError(error_description or "Вход через FSP ID отменён", "FSP_ID_CANCELLED")
        profile = fsp_id_client.complete_login(code or "", st)
        tokens, info = svc.login_via_fsp_id(profile)
    except AppError as e:
        if st["ret"] == "json":
            return JSONResponse(status_code=e.status_code,
                                content={"code": e.code, "message": e.detail, "detail": e.detail})
        return _to_frontend({"error": e.code, "message": e.detail})
    if st["ret"] == "json":
        return FspIdLoginResult(**tokens.model_dump(), **info)
    return _to_frontend({**tokens.model_dump(), **{k: str(v).lower() for k, v in info.items()}})


# ===================================================== имитация FSP ID (Keycloak)
def _mock_enabled():
    if settings.fsp_id_mode != "mock":
        raise NotFound("Имитация FSP ID выключена (FSP_ID_MODE не mock)", "FSP_ID_MOCK_DISABLED")


@mock_router.get("/.well-known/openid-configuration", dependencies=[Depends(_mock_enabled)],
                 summary="Discovery: адреса провайдера (как у Keycloak)")
def discovery():
    return fsp_id_mock.discovery()


@mock_router.get("/protocol/openid-connect/certs", dependencies=[Depends(_mock_enabled)],
                 summary="Ключи провайдера (в имитации id_token подписан HS256 секретом клиента)")
def certs():
    return {"keys": []}


_PAGE_CSP = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"


def _login_page(params: dict, error: str | None = None, email: str = "") -> HTMLResponse:
    e = html.escape
    hidden = "".join(f'<input type="hidden" name="{e(k)}" value="{e(v or "")}">' for k, v in params.items())
    accounts = "".join(
        f"<li><b>{e(a.email)}</b> — {e(a.name)}, "
        f"{('участник № ' + e(a.fsp_id)) if a.fsp_id else 'без номера участника'}</li>"
        for a in fsp_id_mock.ACCOUNTS)
    err = f'<p class="err">{e(error)}</p>' if error else ""
    body = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>FSP ID — вход</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f3f4f6;margin:0;padding:24px;color:#111827}}
.card{{max-width:420px;margin:40px auto;background:#fff;border-radius:16px;padding:28px;box-shadow:0 4px 24px #0001}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#6b7280;margin:0 0 20px;font-size:14px}}
label{{display:block;font-size:14px;margin:12px 0 4px}}
input[type=email],input[type=password]{{width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #d1d5db;
border-radius:8px;font-size:15px}}
button{{margin-top:18px;width:100%;padding:12px;border:0;border-radius:8px;background:#1d4ed8;color:#fff;
font-size:15px;cursor:pointer}}
.err{{background:#fef2f2;color:#991b1b;padding:10px;border-radius:8px;font-size:14px}}
.demo{{margin-top:22px;font-size:13px;color:#374151;background:#f9fafb;border-radius:8px;padding:12px}}
.demo ul{{padding-left:18px;margin:6px 0}} .badge{{display:inline-block;font-size:12px;background:#fef3c7;
color:#92400e;border-radius:6px;padding:2px 8px;margin-bottom:12px}}
</style></head><body><div class="card">
<span class="badge">Имитация FSP ID для хакатона</span>
<h1>Вход через FSP ID</h1><p class="sub">Единый аккаунт Федерации спортивного программирования</p>
{err}<form method="post">{hidden}
<label for="email">Почта</label><input id="email" name="email" type="email" required value="{e(email)}">
<label for="password">Пароль</label><input id="password" name="password" type="password" required>
<button type="submit">Войти</button></form>
<div class="demo">Демо-аккаунты (пароль <b>fsp12345</b>):<ul>{accounts}</ul></div>
</div></body></html>"""
    return HTMLResponse(body, headers={"Content-Security-Policy": _PAGE_CSP})


_AUTH_PARAMS = ("response_type", "client_id", "redirect_uri", "scope", "state", "nonce", "code_challenge",
                "code_challenge_method")


@mock_router.get("/protocol/openid-connect/auth", response_class=HTMLResponse, dependencies=[Depends(_mock_enabled)],
                 summary="Страница входа FSP ID (имитация)")
def authorize_page(request: Request):
    params = {k: request.query_params.get(k) for k in _AUTH_PARAMS}
    try:
        _check_auth_params(params)
    except fsp_id_mock.MockOidcError as e:
        return HTMLResponse(f"<h2>Ошибка запроса входа: {html.escape(e.description)}</h2>", status_code=400,
                            headers={"Content-Security-Policy": _PAGE_CSP})
    return _login_page(params)


def _check_auth_params(params: dict) -> None:
    if params.get("response_type") != "code":
        raise fsp_id_mock.MockOidcError("unsupported_response_type", "Поддерживается только response_type=code")
    if params.get("code_challenge_method") != "S256" or not params.get("code_challenge"):
        raise fsp_id_mock.MockOidcError("invalid_request", "Нужен PKCE (code_challenge_method=S256)")
    fsp_id_mock.check_client(params.get("client_id") or "", params.get("redirect_uri") or "")


@mock_router.post("/protocol/openid-connect/auth", response_class=HTMLResponse, include_in_schema=False,
                  dependencies=[Depends(_mock_enabled)])
async def authorize_submit(request: Request):
    form = await request.form()
    params = {k: form.get(k) for k in _AUTH_PARAMS}
    try:
        _check_auth_params(params)
    except fsp_id_mock.MockOidcError as e:
        return HTMLResponse(f"<h2>Ошибка запроса входа: {html.escape(e.description)}</h2>", status_code=400,
                            headers={"Content-Security-Policy": _PAGE_CSP})
    acc = fsp_id_mock.authenticate(str(form.get("email") or ""), str(form.get("password") or ""))
    if acc is None:
        return _login_page(params, "Неверная почта или пароль FSP ID", str(form.get("email") or ""))
    code = fsp_id_mock.issue_code(acc, client_id=params["client_id"], redirect_uri=params["redirect_uri"],
                                  nonce=params.get("nonce"), code_challenge=params["code_challenge"])
    return RedirectResponse(f"{params['redirect_uri']}?{urlencode({'code': code, 'state': params['state'] or ''})}",
                            status_code=302)


@mock_router.post("/protocol/openid-connect/token", dependencies=[Depends(_mock_enabled)],
                  summary="Обмен кода на токены (имитация)")
def token(grant_type: str = Form(...), code: str = Form(...), redirect_uri: str = Form(...),
          client_id: str = Form(...), client_secret: str = Form(""), code_verifier: str = Form("")):
    if grant_type != "authorization_code":
        return JSONResponse(status_code=400, content={"error": "unsupported_grant_type"})
    try:
        return fsp_id_mock.exchange_code(code=code, client_id=client_id, client_secret=client_secret,
                                         redirect_uri=redirect_uri, code_verifier=code_verifier)
    except fsp_id_mock.MockOidcError as e:
        return JSONResponse(status_code=400, content={"error": e.error, "error_description": e.description})


@mock_router.get("/protocol/openid-connect/userinfo", dependencies=[Depends(_mock_enabled)],
                 summary="Профиль участника FSP ID (имитация)")
def userinfo(request: Request):
    auth = request.headers.get("authorization", "")
    try:
        return fsp_id_mock.userinfo(auth.removeprefix("Bearer ").strip())
    except fsp_id_mock.MockOidcError as e:
        return JSONResponse(status_code=401, content={"error": e.error, "error_description": e.description})
