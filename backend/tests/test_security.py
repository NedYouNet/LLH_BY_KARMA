"""
Тесты безопасности: шифрование ПДн, пароли, перебор, сессии, заголовки, права по 152-ФЗ.
Каждый тест — доказательство конкретного утверждения из защиты проекта.
"""
import base64
import os

import pytest
from sqlalchemy import text

from app.core import crypto
from app.core.config import Settings, check_production_settings, settings
from app.core.rate_limit import limiter
from tests.conftest import ready_candidate, register


# ----------------------------- шифрование -----------------------------
def test_pii_is_encrypted_in_database(client, db):
    h = register(client, "enc@test.ru", full_name="Мария Иванова")
    client.patch("/api/candidate/profile", json={"phone": "+79991112233", "telegram": "@maria"}, headers=h)
    raw = db.execute(text("SELECT full_name, phone, telegram, contact_email FROM candidate_profiles")).one()
    for value in raw:
        assert value.startswith("enc:v1:"), value
    assert "7999" not in raw.phone and "Мария" not in raw.full_name and "@" not in raw.telegram
    prof = client.get("/api/candidate/profile", headers=h).json()  # через API — обычный текст
    assert prof["phone"] == "+79991112233" and prof["full_name"] == "Мария Иванова"


def test_same_value_gives_different_ciphertext_and_tamper_is_detected():
    c = crypto.get_cipher()
    a, b = c.encrypt("+79990000000"), c.encrypt("+79990000000")
    assert a != b  # случайный nonce: по шифротексту не понять, что телефоны одинаковые
    kid, payload = a[len(crypto.PREFIX):].split(":", 1)
    raw = bytearray(base64.b64decode(payload))
    raw[-1] ^= 1  # портим один бит
    with pytest.raises(crypto.DecryptionError):
        c.decrypt(f"{crypto.PREFIX}{kid}:{base64.b64encode(bytes(raw)).decode()}")


def test_key_rotation_reads_old_data():
    k1, k2 = os.urandom(32), os.urandom(32)
    old = crypto.FieldCipher({"k1": k1}, "k1")
    new = crypto.FieldCipher({"k2": k2, "k1": k1}, "k2")
    token = old.encrypt("секрет")
    assert new.decrypt(token) == "секрет" and new.needs_reencrypt(token)
    assert new.encrypt("x").startswith("enc:v1:k2:")


def test_production_refuses_insecure_config():
    bad = Settings(environment="prod", jwt_secret="short", data_encryption_keys="", cors_origins="*")
    assert len(check_production_settings(bad)) == 3
    good = Settings(environment="prod", jwt_secret="x" * 48, cors_origins="https://fsp.example.ru",
                    data_encryption_keys="k1:" + base64.b64encode(os.urandom(32)).decode())
    assert check_production_settings(good) == []


# ----------------------------- пароли и перебор -----------------------------
def test_weak_passwords_rejected(client):
    for pw in ("short1", "onlyletters", "12345678", "password123", "ivanov2026"):
        r = client.post("/api/auth/register", json={"email": "ivanov@test.ru", "password": pw, "role": "candidate"})
        assert r.status_code == 422 and "password" in r.json()["fields"], pw


@pytest.fixture()
def limits_on(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    limiter.reset()
    yield
    limiter.reset()


def test_login_lockout_after_failures(client, limits_on):
    register(client, "brute@test.ru")
    for _ in range(settings.login_max_failures):
        assert client.post("/api/auth/login", json={"email": "brute@test.ru", "password": "guess1234"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "brute@test.ru", "password": "Secure2026x"})
    assert r.status_code == 429 and r.json()["code"] == "ACCOUNT_TEMPORARILY_LOCKED" and "Retry-After" in r.headers


def test_unknown_and_wrong_password_look_the_same(client):
    register(client, "same@test.ru")
    a = client.post("/api/auth/login", json={"email": "same@test.ru", "password": "Wrong2026x"}).json()
    b = client.post("/api/auth/login", json={"email": "nobody@test.ru", "password": "Wrong2026x"}).json()
    assert a == b  # нельзя узнать, зарегистрирован ли email


# ----------------------------- сессии -----------------------------
def _login(client, email):
    return client.post("/api/auth/login", json={"email": email, "password": "Secure2026x"}).json()


def test_refresh_rotation_and_theft_detection(client):
    register(client, "rot@test.ru")
    t1 = _login(client, "rot@test.ru")
    t2 = client.post("/api/auth/refresh", json={"refresh_token": t1["refresh_token"]}).json()
    assert t2["refresh_token"] != t1["refresh_token"]
    stolen = client.post("/api/auth/refresh", json={"refresh_token": t1["refresh_token"]})  # повтор старого
    assert stolen.status_code == 401 and stolen.json()["code"] == "TOKEN_REUSED"
    # вся сессия отозвана — даже свежий токен больше не работает
    assert client.post("/api/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401


def test_logout_revokes_session(client):
    register(client, "out@test.ru")
    t = _login(client, "out@test.ru")
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.post("/api/auth/logout", json={"refresh_token": t["refresh_token"]}, headers=h).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_auth_log_has_no_plain_email(client, db):
    register(client, "log@test.ru")
    client.post("/api/auth/login", json={"email": "log@test.ru", "password": "bad-pass-1"})
    events = db.execute(text("SELECT event, email_hash FROM auth_events")).all()
    assert {"register", "login_success", "login_failed"} <= {e.event for e in events}
    assert all("log@test.ru" not in (e.email_hash or "") for e in events)


# ----------------------------- заголовки -----------------------------
def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"


# ----------------------------- права по 152-ФЗ -----------------------------
def test_export_access_log_and_delete_account(client, db):
    hc = ready_candidate(client, db)
    he = register(client, "hrx@test.ru", role="employer")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={"candidate_id": cid, "message": "Привет", "salary_from": 1,
                                                "salary_to": 2, "contact_method": "hr@x.ru"}, headers=he).json()
    client.patch(f"/api/invitations/{inv['id']}/answer", json={"status": "accepted"}, headers=hc)
    client.get(f"/api/candidates/{cid}", headers=he)  # работодатель посмотрел контакты

    log = client.get("/api/candidate/contact-access-log", headers=hc).json()
    assert log[0]["company_name"] == "ООО Тест" and log[0]["basis"].startswith("invitation_accepted")
    export = client.get("/api/candidate/export", headers=hc).json()
    assert export["account"]["email"] == "cand@test.ru" and len(export["invitations"]) == 1

    bad = client.request("DELETE", "/api/candidate/account", json={"password": "wrong"}, headers=hc)
    assert bad.status_code == 401
    ok = client.request("DELETE", "/api/candidate/account", json={"password": "Secure2026x"}, headers=hc)
    assert ok.status_code == 204
    assert db.execute(text("SELECT count(*) FROM candidate_profiles")).scalar() == 0
    assert db.execute(text("SELECT count(*) FROM invitations")).scalar() == 0
    assert client.post("/api/auth/login", json={"email": "cand@test.ru", "password": "Secure2026x"}).status_code == 401


def test_health_shows_build_fingerprint(client, tmp_path):
    """Отпечаток кода в /api/health: разный код — разный отпечаток, переносы строк Windows не влияют."""
    from app.core.buildinfo import fingerprint_of
    body = client.get("/api/health").json()
    assert body["version"] == "1.4.0" and len(body["build"]["code"]) == 12 and "migration" in body["build"]
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.py").write_bytes(b"x = 1\ny = 2\n")
    lf = fingerprint_of(tmp_path)
    (tmp_path / "app" / "a.py").write_bytes(b"x = 1\r\ny = 2\r\n")     # тот же код, сохранённый в Windows
    assert fingerprint_of(tmp_path) == lf
    (tmp_path / "app" / "a.py").write_bytes(b"x = 1\ny = 3\n")         # код изменился
    assert fingerprint_of(tmp_path) != lf
