"""Главная механика: подборка -> приглашение -> раскрытие контактов. И ограничения доступа."""
from tests.conftest import SURVEY, ready_candidate, register

INVITE = {"position_title": "Junior Python-разработчик", "message": "Приглашаем на интервью в платёжную команду",
          "salary_from": 120000, "salary_to": 160000, "contact_method": "Telegram @hr_anna"}


def test_search_hides_contacts_and_explains(client, db):
    ready_candidate(client, db)
    he = register(client, "hr@test.ru", role="employer")
    r = client.post("/api/candidates/search", json={"specialization": "backend", "skills": ["Python", "Kafka"]}, headers=he)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1 and body["categories"][0]["category"] == "Бэкенд · Junior"
    card = body["items"][0]
    assert card["contacts"] is None and card["contacts_visible"] is False
    assert card["display_name"] == "Иван П."  # фамилия скрыта
    types = {x["type"] for x in card["reasons"]}
    assert {"test", "skills", "fsp"} <= types
    assert "Kafka" in next(x for x in card["reasons"] if x["type"] == "skills")["missing"]


def test_employer_cannot_steal_email_without_accept(client, db):
    """Тест безопасности из инструкции капитана."""
    ready_candidate(client, db)
    he = register(client, "thief@test.ru", role="employer")
    cid = client.post("/api/candidates/search", json={}, headers=he).json()["items"][0]["id"]
    detail = client.get(f"/api/candidates/{cid}", headers=he).json()
    assert detail["contacts"] is None
    assert "cand@test.ru" not in str(detail) and "+7999" not in str(detail)

    inv = client.post("/api/invitations", json={**INVITE, "candidate_id": cid}, headers=he).json()
    assert inv["status"] == "sent"
    # приглашение отправлено, но не принято — контактов всё ещё нет
    assert client.get(f"/api/candidates/{cid}", headers=he).json()["contacts"] is None


def test_full_invitation_flow_reveals_contacts(client, db):
    hc = ready_candidate(client, db)
    he = register(client, "hr2@test.ru", role="employer")
    cid = client.post("/api/candidates/search", json={}, headers=he).json()["items"][0]["id"]

    bad = client.post("/api/invitations", json={**INVITE, "candidate_id": cid, "salary_from": 200000,
                                                "salary_to": 100000}, headers=he)
    assert bad.status_code == 422  # вилка «от» больше «до»
    no_salary = {k: v for k, v in INVITE.items() if k != "salary_to"}
    assert client.post("/api/invitations", json={**no_salary, "candidate_id": cid}, headers=he).status_code == 422

    inv = client.post("/api/invitations", json={**INVITE, "candidate_id": cid}, headers=he).json()
    dup = client.post("/api/invitations", json={**INVITE, "candidate_id": cid}, headers=he)
    assert dup.status_code == 409 and dup.json()["code"] == "INVITATION_EXISTS"

    inbox = client.get("/api/invitations", headers=hc).json()
    assert len(inbox) == 1 and inbox[0]["salary_from"] == 120000 and inbox[0]["company"]["company_name"] == "ООО Тест"
    assert client.get(f"/api/invitations/{inv['id']}", headers=hc).json()["status"] == "viewed"
    assert client.get("/api/invitations", headers=he).json()[0]["status"] == "viewed"  # работодатель видит статус

    acc = client.post(f"/api/invitations/{inv['id']}/accept", json={"reply": "Готов созвониться"}, headers=hc)
    assert acc.status_code == 200 and acc.json()["status"] == "accepted"

    detail = client.get(f"/api/candidates/{cid}", headers=he).json()
    assert detail["contacts_visible"] and detail["contacts"]["email"] == "cand@test.ru"
    assert detail["contacts"]["phone"] == "+79990001122" and detail["display_name"] == "Иван Петров"

    # повторно принять / отозвать принятое — нельзя
    assert client.post(f"/api/invitations/{inv['id']}/accept", headers=hc).status_code == 409
    assert client.post(f"/api/invitations/{inv['id']}/withdraw", headers=he).status_code == 409


def test_contact_reveal_is_logged(client, db):
    from app.models import ContactAccessLog
    hc = ready_candidate(client, db)
    he = register(client, "hr3@test.ru", role="employer")
    cid = client.post("/api/candidates/search", json={}, headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={**INVITE, "candidate_id": cid}, headers=he).json()
    client.post(f"/api/invitations/{inv['id']}/accept", headers=hc)
    client.get(f"/api/candidates/{cid}", headers=he)
    assert db.query(ContactAccessLog).count() == 1


def test_other_employer_still_blind_after_accept(client, db):
    hc = ready_candidate(client, db)
    he1 = register(client, "a1@test.ru", role="employer")
    he2 = register(client, "a2@test.ru", role="employer", company_name="ООО Другая")
    cid = client.post("/api/candidates/search", json={}, headers=he1).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={**INVITE, "candidate_id": cid}, headers=he1).json()
    client.post(f"/api/invitations/{inv['id']}/accept", headers=hc)
    assert client.get(f"/api/candidates/{cid}", headers=he2).json()["contacts"] is None


def test_candidate_sees_only_own_invitations(client, db):
    ready_candidate(client, db, email="c1@test.ru")
    h2 = ready_candidate(client, db, email="c2@test.ru", full_name="Пётр Сидоров")
    he = register(client, "hr4@test.ru", role="employer")
    items = client.post("/api/candidates/search", json={}, headers=he).json()["items"]
    c1 = next(i for i in items if i["display_name"].startswith("Иван"))["id"]
    inv = client.post("/api/invitations", json={**INVITE, "candidate_id": c1}, headers=he).json()
    assert client.get("/api/invitations", headers=h2).json() == []
    assert client.get(f"/api/invitations/{inv['id']}", headers=h2).status_code == 404
    assert client.post(f"/api/invitations/{inv['id']}/accept", headers=h2).status_code == 404


def test_hidden_without_consent(client, db):
    h = register(client, "hidden@test.ru", full_name="Скрытый Кандидат")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    from tests.conftest import pass_test
    pass_test(client, db, h)
    he = register(client, "hr5@test.ru", role="employer")
    assert client.post("/api/candidates/search", json={}, headers=he).json()["total"] == 0


def test_fsp_link_and_candidate_without_fsp_ranked(client, db):
    hc1 = ready_candidate(client, db, email="fsp@test.ru", full_name="Анна Смирнова")
    ready_candidate(client, db, email="nofsp@test.ru", full_name="Олег Орлов")
    r = client.post("/api/candidate/fsp", json={"fsp_id": "123457"}, headers=hc1)
    assert r.status_code == 200 and r.json()["fsp_achievements"] and r.json()["fsp_score"] > 0
    assert client.post("/api/candidate/fsp", json={"fsp_id": "99999"}, headers=hc1).status_code == 404

    he = register(client, "hr6@test.ru", role="employer")
    body = client.post("/api/candidates/search", json={}, headers=he).json()
    assert body["total"] == 2  # кандидат без ФСП НЕ исчез из выдачи
    assert body["items"][0]["has_fsp"] is True  # но с ФСП — выше при равном тесте
    no_fsp = body["items"][1]
    assert any("Нет истории ФСП" in r["label"] for r in no_fsp["reasons"])
    only = client.post("/api/candidates/search", json={"fsp_only": True}, headers=he).json()
    assert only["total"] == 1


def test_participant_without_events(client, db):
    hc = ready_candidate(client, db)
    r = client.post("/api/candidate/fsp", json={"fsp_id": "123450"}, headers=hc)
    assert r.status_code == 200 and r.json()["fsp_achievements"] == [] and r.json()["fsp_score"] == 0
