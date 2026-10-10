"""
Приёмка по документу фронтенда «Как понять, что первая интеграция готова» (раздел 7).
Каждый тест = один пункт чек-листа.
"""
from tests.conftest import ready_candidate, register

NEED = {"title": "Бэкендер", "specialization": "backend", "grade": "junior",
        "stack": ["python", "PostgreSQL", "Docker"], "description": "Платёжный сервис"}
OFFER = {"message": "Разработка API для платёжного сервиса", "salary_from": 70000, "salary_to": 100000,
         "contact_method": "hr@example.com"}


def test_1_company_and_needs_persist(client):
    he = register(client, "need@test.ru", role="employer")
    client.patch("/api/employer/profile", json={"description": "Финтех", "industry": "fintech"}, headers=he)
    n = client.post("/api/employer/needs", json=NEED, headers=he).json()
    assert n["stack"] == ["Python", "PostgreSQL", "Docker"]
    upd = client.put(f"/api/employer/needs/{n['id']}", json={**NEED, "grade": "middle"}, headers=he).json()
    assert upd["grade"] == "middle"
    # «обновили страницу» — читаем заново
    assert client.get("/api/employer/profile", headers=he).json()["description"] == "Финтех"
    assert client.get("/api/employer/needs", headers=he).json()[0]["grade"] == "middle"
    other = register(client, "other@test.ru", role="employer")
    assert client.get(f"/api/employer/needs/{n['id']}", headers=other).status_code == 404


def test_2_search_by_need_and_fsp_filter(client, db):
    hc = ready_candidate(client, db, email="f@test.ru", full_name="Анна Смирнова")
    client.post("/api/candidate/fsp", json={"fsp_id": "123457"}, headers=hc)
    ready_candidate(client, db, email="n@test.ru", full_name="Олег Орлов")
    he = register(client, "hr@test.ru", role="employer")
    need = client.post("/api/employer/needs", json=NEED, headers=he).json()
    body = client.get(f"/api/candidates?needs_id={need['id']}", headers=he).json()
    assert body["total"] == 2
    card = body["items"][0]
    assert card["grade_verified"] and card["category_id"] == "backend:junior" and card["test_max_score"] == 100
    assert set(card["matched_skills"]) <= {"Python", "PostgreSQL", "Docker"}
    assert card["fsp_verification"] == "demo"  # демо-данные помечены честно
    assert body["items"][1]["fsp_verification"] == "none" and body["items"][1]["has_fsp"] is False
    only = client.get("/api/candidates?only_fsp=true&stack=Python,Docker", headers=he).json()
    assert only["total"] == 1
    empty = client.get("/api/candidates?specialization=devops", headers=he).json()
    assert empty == {**empty, "items": [], "total": 0}


def test_3_salary_validation_points_to_field(client, db):
    ready_candidate(client, db)
    he = register(client, "hr3@test.ru", role="employer")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    r = client.post("/api/invitations", json={**OFFER, "candidate_id": cid, "salary_from": 100000, "salary_to": 70000},
                    headers=he)
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR" and "salary_to" in r.json()["fields"]
    r = client.post("/api/invitations", json={**OFFER, "candidate_id": cid, "salary_from": 0}, headers=he)
    assert r.status_code == 422 and "salary_from" in r.json()["fields"]
    ok = client.post("/api/invitations", json={**OFFER, "candidate_id": cid}, headers=he)
    assert ok.status_code == 201 and ok.json()["currency"] == "RUB" and ok.json()["status"] == "sent"
    assert ok.json()["position_title"] == "Предложение о работе"


def test_4_5_candidate_answers_and_employer_sees_contacts(client, db):
    hc = ready_candidate(client, db)
    he = register(client, "hr4@test.ru", role="employer")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={**OFFER, "candidate_id": cid}, headers=he).json()
    seen = client.get("/api/invitations", headers=hc).json()[0]
    assert seen["company"]["company_name"] and seen["salary_from"] == 70000 and seen["contact_method"]
    r = client.patch(f"/api/invitations/{inv['id']}/answer", json={"status": "accepted"}, headers=hc)
    assert r.status_code == 200 and r.json()["status"] == "accepted" and r.json()["updated_at"]
    again = client.patch(f"/api/invitations/{inv['id']}/answer", json={"status": "rejected"}, headers=hc)
    assert again.status_code == 409
    assert client.get("/api/invitations", headers=he).json()[0]["status"] == "accepted"
    assert client.get(f"/api/candidates/{cid}", headers=he).json()["contacts_visible"] is True


def test_5_rejected_keeps_contacts_closed(client, db):
    hc = ready_candidate(client, db)
    he = register(client, "hr5@test.ru", role="employer")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={**OFFER, "candidate_id": cid}, headers=he).json()
    client.patch(f"/api/invitations/{inv['id']}/answer", json={"status": "rejected"}, headers=hc)
    detail = client.get(f"/api/candidates/{cid}", headers=he).json()
    assert detail["contacts"] is None and detail["contacts_visible"] is False


def test_logout_and_error_format(client):
    h = register(client, "lo@test.ru")
    assert client.post("/api/auth/logout", headers=h).status_code == 204
    r = client.get("/api/candidate/profile")
    assert r.status_code == 401 and set(r.json()) >= {"code", "message"}
