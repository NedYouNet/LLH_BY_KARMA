"""Интеграция с ATS работодателя: настройка, подписанные события, журнал, защита от SSRF."""
import hashlib
import hmac
import json

import httpx
import pytest

from app.core.config import settings
from app.services import ats_service
from tests.conftest import ready_candidate, register


@pytest.fixture()
def ats_inbox(monkeypatch):
    """Подменяем сетевой вызов: складываем «отправленные в ATS» запросы в список."""
    inbox = []

    def fake_post(url, body, headers):
        inbox.append({"url": url, "body": body, "headers": headers})
        return httpx.Response(200)
    monkeypatch.setattr(ats_service, "_post", fake_post)
    return inbox


def test_configure_test_event_and_signature(client, ats_inbox):
    he = register(client, "hr@test.ru", role="employer")
    cfg = client.put("/api/employer/integrations/ats", json={"webhook_url": "https://ats.example.ru/hook"},
                     headers=he).json()
    secret = cfg["secret"]
    assert cfg["enabled"] and secret.startswith("whsec_") and cfg["secret_hint"] == "…" + secret[-4:]
    assert client.get("/api/employer/integrations/ats", headers=he).json()["secret"] is None  # показан один раз
    d = client.post("/api/employer/integrations/ats/test", headers=he).json()
    assert d["ok"] is True and d["event"] == "ats.test"
    sent = ats_inbox[0]
    expected = "sha256=" + hmac.new(secret.encode(), sent["headers"]["X-FSP-Timestamp"].encode() + b"." + sent["body"],
                                    hashlib.sha256).hexdigest()
    assert sent["headers"]["X-FSP-Signature"] == expected and sent["headers"]["X-FSP-Event"] == "ats.test"
    assert client.get("/api/employer/integrations/ats", headers=he).json()["recent_deliveries"][0]["ok"] is True


def test_accepted_invitation_is_sent_to_ats_and_logged(client, db, ats_inbox):
    h = ready_candidate(client, db)
    he = register(client, "hr@test.ru", role="employer")
    client.put("/api/employer/integrations/ats", json={"webhook_url": "https://ats.example.ru/hook"}, headers=he)
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={"candidate_id": cid, "message": "Привет", "salary_from": 100000,
                                                "salary_to": 150000}, headers=he).json()
    assert not ats_inbox  # до принятия в ATS ничего не уходит
    client.post(f"/api/invitations/{inv['id']}/accept", json={"reply": "Готов"}, headers=h)
    event = json.loads(ats_inbox[0]["body"])
    assert event["event"] == "invitation.accepted" and event["invitation"]["candidate_reply"] == "Готов"
    assert event["candidate"]["full_name"] == "Иван Петров" and event["candidate"]["phone"] == "+79990001122"
    log = client.get("/api/candidate/contact-access-log", headers=h).json()
    assert any("ats_webhook" in str(row) for row in log)


def test_unreachable_ats_is_recorded_not_raised(client, monkeypatch):
    def broken(url, body, headers):
        raise httpx.ConnectError("нет связи")
    monkeypatch.setattr(ats_service, "_post", broken)
    he = register(client, "hr@test.ru", role="employer")
    client.put("/api/employer/integrations/ats", json={"webhook_url": "https://ats.example.ru/hook"}, headers=he)
    d = client.post("/api/employer/integrations/ats/test", headers=he).json()
    assert d["ok"] is False and "ConnectError" in d["error"]


def test_bad_and_internal_urls_are_rejected(client, monkeypatch):
    he = register(client, "hr@test.ru", role="employer")
    r = client.put("/api/employer/integrations/ats", json={"webhook_url": "ftp://x"}, headers=he)
    assert r.status_code == 400 and "webhook_url" in r.json()["fields"]
    monkeypatch.setattr(settings, "environment", "prod")
    for url in ("http://ats.example.ru/hook", "https://127.0.0.1/hook", "https://10.0.0.5/hook"):
        r = client.put("/api/employer/integrations/ats", json={"webhook_url": url}, headers=he)
        assert r.status_code == 400, url
    assert client.delete("/api/employer/integrations/ats", headers=he).status_code == 204


# ------------------------- встроенный тестовый приёмник (имитация ATS) -------------------------
@pytest.fixture()
def loopback(client, monkeypatch):
    """Отправка из платформы идёт по-настоящему — в наш же приёмник /api/mock-ats/webhook (без сети)."""
    from urllib.parse import urlparse

    def post_to_self(url, body, headers):
        r = client.post(urlparse(url).path, content=body, headers=headers)
        return httpx.Response(r.status_code, content=r.content)
    monkeypatch.setattr(ats_service, "_post", post_to_self)


def test_mock_receiver_gets_signed_events_end_to_end(client, db, loopback):
    from app.services.ats_mock import mock_url
    h = ready_candidate(client, db)
    he = register(client, "hr@test.ru", role="employer")
    client.put("/api/employer/integrations/ats", json={"webhook_url": mock_url()}, headers=he)
    d = client.post("/api/employer/integrations/ats/test", headers=he).json()
    assert d["ok"] is True and d["status_code"] == 200          # приёмник принял и проверил подпись
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={"candidate_id": cid, "message": "Привет", "salary_from": 100000,
                                                "salary_to": 150000}, headers=he).json()
    client.post(f"/api/invitations/{inv['id']}/accept", json={"reply": "Готов"}, headers=h)
    events = client.get("/api/mock-ats/events", headers=he).json()
    assert [e["event"] for e in events] == ["invitation.accepted", "ats.test"]   # новые сверху
    assert all(e["signature_valid"] for e in events)
    assert events[0]["payload"]["candidate"]["full_name"] == "Иван Петров"
    # тело с контактами в БД зашифровано
    from sqlalchemy import text
    raw = db.execute(text("SELECT payload FROM mock_ats_events ORDER BY id DESC LIMIT 1")).scalar()
    assert raw.startswith("enc:v1:") and "Иван" not in raw


def _signed(secret, body: bytes, ts: int, event_id="e1"):
    from app.services.ats_service import sign
    return {"X-FSP-Timestamp": str(ts), "X-FSP-Signature": sign(secret, str(ts), body),
            "X-FSP-Event": "ats.test", "X-FSP-Event-Id": event_id, "Content-Type": "application/json"}


def test_mock_receiver_rejects_forged_old_and_ignores_duplicates(client):
    import time
    from app.services.ats_mock import mock_url
    he = register(client, "hr@test.ru", role="employer")
    secret = client.put("/api/employer/integrations/ats", json={"webhook_url": mock_url()}, headers=he).json()["secret"]
    body = b'{"event": "ats.test"}'
    now = int(time.time())
    ok = client.post("/api/mock-ats/webhook", content=body, headers=_signed(secret, body, now))
    assert ok.status_code == 200 and ok.json()["duplicate"] is False
    again = client.post("/api/mock-ats/webhook", content=body, headers=_signed(secret, body, now))
    assert again.json()["duplicate"] is True and len(client.get("/api/mock-ats/events", headers=he).json()) == 1
    forged = client.post("/api/mock-ats/webhook", content=b'{"event": "hacked"}',
                         headers=_signed(secret, body, now, "e2"))      # тело подменили после подписи
    assert forged.status_code == 401 and forged.json()["code"] == "SIGNATURE_INVALID"
    wrong_key = client.post("/api/mock-ats/webhook", content=body, headers=_signed("whsec_чужой", body, now, "e3"))
    assert wrong_key.status_code == 401
    old = client.post("/api/mock-ats/webhook", content=body, headers=_signed(secret, body, now - 3600, "e4"))
    assert old.status_code == 401 and old.json()["code"] == "WEBHOOK_EXPIRED"
    assert client.post("/api/mock-ats/webhook", content=body).status_code == 400   # без заголовков


def test_mock_receiver_events_are_private_and_off_in_prod(client, monkeypatch, loopback):
    from app.services.ats_mock import mock_url
    he = register(client, "hr@test.ru", role="employer")
    other = register(client, "hr2@test.ru", role="employer", company_name="ООО Другая")
    client.put("/api/employer/integrations/ats", json={"webhook_url": mock_url()}, headers=he)
    client.post("/api/employer/integrations/ats/test", headers=he)
    assert len(client.get("/api/mock-ats/events", headers=he).json()) == 1
    assert client.get("/api/mock-ats/events", headers=other).json() == []       # чужие события не видны
    hc = register(client, "cand@test.ru")
    assert client.get("/api/mock-ats/events", headers=hc).status_code == 403      # кандидату нельзя
    monkeypatch.setattr(settings, "environment", "prod")
    assert client.post("/api/mock-ats/webhook", content=b"{}").status_code == 404
