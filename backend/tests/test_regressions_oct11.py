"""Ошибки, найденные при проверке сборки main 11 октября: каждая закреплена тестом."""
from datetime import timedelta

from starlette.requests import Request

from app.core import rate_limit
from app.core.database import utcnow
from app.models import TestAttempt
from tests.conftest import SURVEY, register
from tests.test_vacancies_and_tasks import VACANCY


def test_vacancy_salary_cannot_be_erased(client):
    """Раньше PATCH с salary_from: null ронял сервер (500). Теперь — понятная ошибка 400."""
    he = register(client, "sal@test.ru", role="employer")
    v = client.post("/api/vacancies", json=VACANCY, headers=he).json()
    r = client.patch(f"/api/vacancies/{v['id']}", json={"salary_from": None}, headers=he)
    assert r.status_code == 400 and r.json()["code"] == "SALARY_REQUIRED"
    r = client.patch(f"/api/vacancies/{v['id']}", json={"title": None}, headers=he)
    assert r.status_code == 400 and r.json()["code"] == "FIELD_REQUIRED"
    still = client.get(f"/api/vacancies/{v['id']}", headers=he).json()
    assert still["salary_from"] == 100000 and still["title"] == VACANCY["title"]


def test_expired_attempt_has_result_and_is_not_offered_to_continue(client, db):
    """Брошенный тест после дедлайна: «Время вышло», а не «Тест ещё не завершён»; грейд не меняется."""
    h = register(client, "late@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    a = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "junior"},
                    headers=h).json()
    assert client.get("/api/candidate/category", headers=h).json()["active_attempt_id"] == a["id"]
    row = db.get(TestAttempt, a["id"])
    row.deadline_at = utcnow() - timedelta(hours=1)
    db.commit()

    st = client.get("/api/candidate/category", headers=h).json()
    assert st["active_attempt_id"] is None and st["grade"] is None
    res = client.get(f"/api/testing/attempts/{a['id']}/result", headers=h)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "expired" and body["score"] == 0 and body["passed"] is False
    assert body["decision"]["changed"] is False and "истекло" in body["decision"]["message"]
    # после просрочки можно начать заново (тот же уровень сразу не даёт кулдаун — уровень ниже доступен)
    assert client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "intern"},
                       headers=h).status_code == 201


def _request(xff: str | None, peer: str = "172.18.0.5") -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_client_ip_behind_nginx_uses_last_forwarded_address(monkeypatch):
    """За nginx каждый пользователь — свой адрес; подставной X-Forwarded-For не помогает обойти лимиты."""
    monkeypatch.setattr(rate_limit.settings, "trust_proxy_headers", True)
    assert rate_limit.client_ip(_request("203.0.113.7")) == "203.0.113.7"
    assert rate_limit.client_ip(_request("1.2.3.4, 203.0.113.7")) == "203.0.113.7"  # 1.2.3.4 прислал сам клиент
    assert rate_limit.client_ip(_request(None)) == "172.18.0.5"
    monkeypatch.setattr(rate_limit.settings, "trust_proxy_headers", False)
    assert rate_limit.client_ip(_request("203.0.113.7")) == "172.18.0.5"
