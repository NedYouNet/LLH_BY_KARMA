"""Правки по ответам организаторов (сессия Q&A): неподтверждённый грейд, ФСП, gross/net, отзыв контактов."""
from tests.conftest import SURVEY, ready_candidate, register


def untested_candidate(client, email="untested@test.ru", **survey):
    """Анкета и согласия есть, тест не пройден."""
    h = register(client, email, full_name="Пётр Непроверенный")
    client.patch("/api/candidate/profile", json={"phone": "+79990000000"}, headers=h)
    r = client.post("/api/candidate/survey", json={**SURVEY, **survey}, headers=h)
    assert r.status_code == 200, r.text
    client.put("/api/candidate/consents", json={"consent_processing": True, "consent_publication": True}, headers=h)
    return h


def test_unverified_grade_is_shown_with_status_and_ranked_lower(client, db):
    ready_candidate(client, db)  # прошёл тест: Бэкенд · Junior
    untested_candidate(client)   # заявил Бэкенд · Junior, теста нет
    he = register(client, "hr@test.ru", role="employer")
    res = client.get("/api/candidates", params={"specialization": "backend", "grade": "junior"}, headers=he).json()
    assert res["total"] == 2
    first, second = res["items"]
    assert first["grade_verified"] is True and second["grade_verified"] is False   # неподтверждённый — ниже
    assert second["grade"] == "junior" and second["category"] == "Бэкенд · Junior"
    assert second["grade_status_label"].startswith("Не подтверждён") and second["test_score"] is None
    assert any(r["type"] == "test" and not r["positive"] and "не пройден" in r["label"] for r in second["reasons"])
    assert second["breakdown"]["grade_multiplier"] == 0.6
    bucket = res["categories"][0]
    assert (bucket["count"], bucket["verified"], bucket["unverified"]) == (2, 1, 1)
    # фильтр «только подтверждённые»
    only = client.get("/api/candidates", params={"specialization": "backend", "only_verified": "true"},
                      headers=he).json()
    assert only["total"] == 1 and only["items"][0]["grade_verified"] is True
    # обзор категорий тоже считает обе группы
    overview = client.get("/api/candidates/categories", headers=he).json()
    assert overview[0]["verified"] == 1 and overview[0]["unverified"] == 1


def test_unverified_candidate_can_be_invited_and_is_visible_in_onboarding(client, db):
    h = untested_candidate(client)
    me = client.get("/api/auth/me", headers=h).json()
    assert me["onboarding"]["visible_to_employers"] is True and me["onboarding"]["test_passed"] is False
    he = register(client, "hr@test.ru", role="employer")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    r = client.post("/api/invitations", json={"candidate_id": cid, "message": "Пройдите тест и приходите",
                                              "salary_from": 100000, "salary_to": 150000}, headers=he)
    assert r.status_code == 201, r.text


def test_survey_industry_is_optional(client):
    h = register(client, "c@test.ru")
    body = {"specialization": "frontend", "declared_grade": "junior"}
    r = client.post("/api/candidate/survey", json=body, headers=h)
    assert r.status_code == 200 and r.json()["industry"] is None
    assert r.json()["declared_specialization"] == "frontend"
    bad = client.post("/api/candidate/survey", json={**body, "industry": "космос"}, headers=h)
    assert bad.status_code == 422


def test_fsp_score_counts_results_not_competition_level():
    from app.services.fsp_service import compute_fsp_score
    win = [{"event": "Хакатон", "level": "municipal", "place": 1}]
    win_rus = [{"event": "Чемпионат России", "level": "all_russian", "place": 1}]
    assert compute_fsp_score(win) == compute_fsp_score(win_rus)            # соревнования равно важны
    attendances = [{"event": f"Отбор {i}", "result": "Участник"} for i in range(30)]
    assert compute_fsp_score(attendances) < compute_fsp_score(win)         # явками профиль не набить
    assert compute_fsp_score(attendances) == compute_fsp_score(attendances[:4])  # потолок за непризовое
    assert compute_fsp_score(win + [{"place": 2}]) > compute_fsp_score(win)      # больше призов — выше
    assert compute_fsp_score([]) == 0


def _accepted_invitation(client, db, salary_type="net"):
    h = ready_candidate(client, db)
    he = register(client, "hr@test.ru", role="employer")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    inv = client.post("/api/invitations", json={"candidate_id": cid, "message": "Привет", "salary_from": 150000,
                                                "salary_to": 200000, "salary_type": salary_type}, headers=he).json()
    assert client.post(f"/api/invitations/{inv['id']}/accept", headers=h).status_code == 200
    return h, he, cid, inv


def test_salary_type_is_explicit(client, db):
    _, he, _, inv = _accepted_invitation(client, db, salary_type="net")
    assert inv["salary_type"] == "net" and inv["salary_type_label"] == "на руки" and inv["currency"] == "RUB"
    v = client.post("/api/vacancies", json={"title": "Бэкенд", "description": "Пишем API на Python",
                                            "specialization": "backend", "grade": "junior", "salary_from": 100000,
                                            "salary_to": 150000}, headers=he).json()
    assert v["salary_type"] == "gross" and v["salary_type_label"] == "до вычета НДФЛ"  # по умолчанию
    bad = client.post("/api/invitations", json={"candidate_id": 1, "message": "x", "salary_from": 1, "salary_to": 2,
                                                "salary_type": "наличными"}, headers=he)
    assert bad.status_code == 422 and "salary_type" in bad.json()["fields"]


def test_candidate_can_revoke_and_restore_contact_access(client, db):
    h, he, cid, inv = _accepted_invitation(client, db)
    assert client.get(f"/api/candidates/{cid}", headers=he).json()["contacts"] is not None
    r = client.put(f"/api/invitations/{inv['id']}/contact-access", json={"granted": False}, headers=h)
    assert r.status_code == 200 and r.json()["contacts_revoked"] is True
    card = client.get(f"/api/candidates/{cid}", headers=he).json()
    assert card["contacts"] is None and card["contacts_visible"] is False and card["display_name"] == "Иван П."
    client.put(f"/api/invitations/{inv['id']}/contact-access", json={"granted": True}, headers=h)
    assert client.get(f"/api/candidates/{cid}", headers=he).json()["contacts"]["phone"] == "+79990001122"
    # работодатель управлять доступом не может
    assert client.put(f"/api/invitations/{inv['id']}/contact-access", json={"granted": True},
                      headers=he).status_code == 403
