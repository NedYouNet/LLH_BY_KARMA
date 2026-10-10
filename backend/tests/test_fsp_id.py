"""Вход через FSP ID: OpenID Connect (Authorization Code + PKCE) против встроенной имитации Keycloak."""
from urllib.parse import parse_qs, urlparse

import jwt

from tests.conftest import register


def _path(url: str) -> str:
    u = urlparse(url)
    return u.path + ("?" + u.query if u.query else "")


def start(client, return_to="json"):
    r = client.get("/api/auth/fsp-id/login", params={"return_to": return_to}, follow_redirects=False)
    assert r.status_code == 302
    auth_url = r.headers["location"]
    assert "/api/mock-fsp-id/realms/fsp/protocol/openid-connect/auth" in auth_url
    params = {k: v[0] for k, v in parse_qs(urlparse(auth_url).query).items()}
    assert params["code_challenge_method"] == "S256" and params["response_type"] == "code"
    return auth_url, params


def sign_in(client, email, password="fsp12345", return_to="json"):
    """Проходит весь путь: наш /login -> страница FSP ID -> /callback. Возвращает ответ callback."""
    auth_url, params = start(client, return_to)
    page = client.get(_path(auth_url))
    assert page.status_code == 200 and "Вход через FSP ID" in page.text
    r = client.post(_path(auth_url).split("?")[0], data={**params, "email": email, "password": password},
                    follow_redirects=False)
    assert r.status_code == 302, r.text
    return client.get(_path(r.headers["location"]), follow_redirects=False)


def test_config_lists_demo_accounts(client):
    cfg = client.get("/api/auth/fsp-id/config").json()
    assert cfg["enabled"] is True and cfg["mode"] == "mock" and cfg["login_url"] == "/api/auth/fsp-id/login"
    assert any(a["fsp_id"] is None for a in cfg["demo_accounts"])  # аккаунт без номера участника тоже есть
    disc = client.get("/api/mock-fsp-id/realms/fsp/.well-known/openid-configuration").json()
    assert disc["issuer"].endswith("/api/mock-fsp-id/realms/fsp") and "S256" in disc["code_challenge_methods_supported"]


def test_new_participant_gets_account_and_fsp_achievements(client):
    r = sign_in(client, "maria.fsp@demo.ru")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is True and body["fsp_linked"] is True and body["role"] == "candidate"
    h = {"Authorization": f"Bearer {body['access_token']}"}
    prof = client.get("/api/candidate/profile", headers=h).json()
    assert prof["full_name"] == "Мария Иванова" and prof["fsp_id"] == "100245" and prof["fsp_achievements"]
    assert prof["consent_publication"] is False  # согласия на публикацию даёт сам кандидат, не FSP ID
    again = sign_in(client, "maria.fsp@demo.ru").json()
    assert again["created"] is False  # второй вход — тот же пользователь по sub


def test_existing_account_is_linked_by_verified_email(client):
    h = register(client, "candidate@demo.ru", full_name="Алексей")
    me = client.get("/api/auth/me", headers=h).json()
    body = sign_in(client, "candidate@demo.ru").json()
    assert body["linked_existing"] is True and body["created"] is False
    me2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
    assert me2["user"]["id"] == me["user"]["id"]


def test_participant_without_number_and_without_history(client):
    body = sign_in(client, "ivan.fsp@demo.ru").json()
    assert body["created"] is True and body["fsp_linked"] is False  # номера нет — штатный случай
    body = sign_in(client, "olga.fsp@demo.ru").json()   # номер есть, соревнований нет
    h = {"Authorization": f"Bearer {body['access_token']}"}
    prof = client.get("/api/candidate/profile", headers=h).json()
    assert prof["fsp_id"] == "100500" and prof["fsp_achievements"] == []


def test_wrong_password_shows_error_on_fsp_id_page(client):
    auth_url, params = start(client)
    r = client.post(_path(auth_url).split("?")[0], data={**params, "email": "maria.fsp@demo.ru", "password": "нет"},
                    follow_redirects=False)
    assert r.status_code == 200 and "Неверная почта или пароль" in r.text


def test_code_is_single_use_and_state_is_signed(client):
    auth_url, params = start(client)
    r = client.post(_path(auth_url).split("?")[0], data={**params, "email": "maria.fsp@demo.ru",
                                                         "password": "fsp12345"}, follow_redirects=False)
    callback = _path(r.headers["location"])
    assert client.get(callback).status_code == 200
    again = client.get(callback)
    assert again.status_code == 400 and again.json()["code"] == "FSP_ID_EXCHANGE_FAILED"
    forged = client.get("/api/auth/fsp-id/callback", params={"code": "x", "state": "подделка"})
    assert forged.status_code == 400 and forged.json()["code"] == "FSP_ID_STATE_INVALID"


def test_redirect_to_frontend_carries_tokens_in_fragment(client):
    r = sign_in(client, "maria.fsp@demo.ru", return_to="frontend")
    assert r.status_code == 302
    loc = urlparse(r.headers["location"])
    assert loc.path == "/auth/fsp-id" and not loc.query
    frag = parse_qs(loc.fragment)
    assert frag["access_token"] and frag["role"] == ["candidate"] and frag["fsp_linked"] == ["true"]


def test_token_and_userinfo_endpoints_speak_oidc(client):
    auth_url, params = start(client)
    verifier = jwt.decode(params["state"], options={"verify_signature": False})["cv"]
    r = client.post(_path(auth_url).split("?")[0], data={**params, "email": "maria.fsp@demo.ru",
                                                         "password": "fsp12345"}, follow_redirects=False)
    code = parse_qs(urlparse(r.headers["location"]).query)["code"][0]
    token_url = "/api/mock-fsp-id/realms/fsp/protocol/openid-connect/token"
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": params["redirect_uri"],
            "client_id": "fsp-talent", "client_secret": "dev-fsp-id-client-secret-change-me"}
    bad = client.post(token_url, data={**form, "code_verifier": "не-тот"})
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_grant"  # PKCE
    ok = client.post(token_url, data={**form, "code_verifier": verifier})
    assert ok.status_code == 200 and ok.json()["token_type"] == "Bearer"
    info = client.get("/api/mock-fsp-id/realms/fsp/protocol/openid-connect/userinfo",
                      headers={"Authorization": f"Bearer {ok.json()['access_token']}"}).json()
    assert info["email"] == "maria.fsp@demo.ru" and info["fsp_id"] == "100245"
