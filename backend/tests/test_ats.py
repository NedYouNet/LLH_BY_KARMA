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
