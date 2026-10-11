"""Дополнительный функционал: вакансии, отклики, короткие задания, PDF."""
from tests.conftest import ready_candidate, register

VACANCY = {"title": "Junior Python-разработчик", "description": "Пишем API на FastAPI для платёжного сервиса",
           "specialization": "backend", "grade": "junior", "skills": ["python", "PostgreSQL", "FastAPI"],
           "salary_from": 100000, "salary_to": 150000, "work_format": "remote"}


def test_vacancy_crud_and_salary_required(client):
    he = register(client, "v@test.ru", role="employer")
    no_salary = {k: v for k, v in VACANCY.items() if k not in ("salary_from", "salary_to")}
    assert client.post("/api/vacancies", json=no_salary, headers=he).status_code == 422
    v = client.post("/api/vacancies", json=VACANCY, headers=he).json()
    assert v["skills"][0] == "Python"  # навыки нормализованы по справочнику
    assert v["category"] == "Бэкенд · Junior"
    upd = client.patch(f"/api/vacancies/{v['id']}", json={"salary_to": 90000}, headers=he)
    assert upd.status_code == 400  # «до» меньше «от»
    assert client.patch(f"/api/vacancies/{v['id']}", json={"status": "closed"}, headers=he).json()["status"] == "closed"


def test_other_employer_cannot_edit_vacancy(client):
    he1 = register(client, "o1@test.ru", role="employer")
    he2 = register(client, "o2@test.ru", role="employer")
    v = client.post("/api/vacancies", json=VACANCY, headers=he1).json()
    assert client.patch(f"/api/vacancies/{v['id']}", json={"title": "Взлом"}, headers=he2).status_code == 404


def test_application_reveals_contacts_to_that_employer(client, db):
    hc = ready_candidate(client, db)
    he = register(client, "ap@test.ru", role="employer")
    v = client.post("/api/vacancies", json=VACANCY, headers=he).json()
    lst = client.get("/api/vacancies", headers=hc).json()
    assert lst["total"] == 1
    app = client.post(f"/api/vacancies/{v['id']}/apply", json={"cover_letter": "Хочу к вам"}, headers=hc)
    assert app.status_code == 201
    assert client.post(f"/api/vacancies/{v['id']}/apply", headers=hc).status_code == 409
    assert client.get("/api/vacancies", headers=hc).json()["items"][0]["my_application_status"] == "sent"

    apps = client.get(f"/api/applications?vacancy_id={v['id']}", headers=he).json()
    assert apps[0]["candidate"]["contacts"]["email"] == "cand@test.ru"  # откликнулся сам -> контакты видны
    r = client.patch(f"/api/applications/{apps[0]['id']}", json={"status": "accepted"}, headers=he)
    assert r.json()["status"] == "accepted"
    assert client.get("/api/applications", headers=hc).json()[0]["status"] == "accepted"


def test_vacancy_matches_and_assessment_preview(client, db):
    ready_candidate(client, db)
    he = register(client, "m@test.ru", role="employer")
    v = client.post("/api/vacancies", json=VACANCY, headers=he).json()
    m = client.get(f"/api/vacancies/{v['id']}/matches", headers=he).json()
    assert m["total"] == 1 and m["items"][0]["match_score"] > 0
    prev = client.get(f"/api/vacancies/{v['id']}/assessment-preview", headers=he).json()
    a, b = prev["sample_variants"]
    assert [i["code"]["examples"] for i in a] != [i["code"]["examples"] for i in b]


def test_short_tasks_affect_activity(client, db):
    hc = ready_candidate(client, db)
    he = register(client, "st@test.ru", role="employer")
    t = client.post("/api/short-tasks", json={"title": "Rate limiter", "description": "Как ограничить 100 rps на пользователя?",
                                               "specialization": "backend"}, headers=he).json()
    feed = client.get("/api/short-tasks/feed", headers=hc).json()
    assert feed[0]["id"] == t["id"]
    s = client.post(f"/api/short-tasks/{t['id']}/submit", json={"answer": "Token bucket в Redis"}, headers=hc).json()
    assert client.post(f"/api/short-tasks/{t['id']}/submit", json={"answer": "ещё раз"}, headers=hc).status_code == 409
    subs = client.get(f"/api/short-tasks/{t['id']}/submissions", headers=he).json()
    assert subs[0]["candidate"]["contacts"] is None  # решение задания не раскрывает контакты
    r = client.post(f"/api/short-tasks/submissions/{s['id']}/review", json={"score": 9}, headers=he)
    assert r.json()["employer_score"] == 9
    prof = client.get("/api/candidate/profile", headers=hc).json()
    assert prof["short_tasks_done"] == 1 and prof["short_tasks_avg"] == 9


def test_profile_pdf(client, db):
    hc = ready_candidate(client, db)
    r = client.get("/api/candidate/profile/pdf", headers=hc)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_resume_parse_fallback(client):
    from reportlab.pdfgen import canvas
    import io
    from app.services import pdf_service  # регистрирует шрифт с кириллицей
    buf = io.BytesIO()
    cv = canvas.Canvas(buf)
    cv.setFont(pdf_service._FONT, 12)
    for n, line in enumerate(["Иван Петров", "ivan@mail.ru +7 999 123-45-67", "Python, FastAPI, PostgreSQL, Docker",
                              "Опыт работы 3 года"]):
        cv.drawString(50, 800 - n * 20, line)
    cv.save()
    hc = register(client, "cv@test.ru")
    r = client.post("/api/candidate/resume/parse", files={"file": ("cv.pdf", buf.getvalue(), "application/pdf")}, headers=hc)
    assert r.status_code == 200, r.text
    f = r.json()["fields"]
    assert r.json()["source"] == "fallback"
    assert {"Python", "FastAPI", "PostgreSQL", "Docker"} <= set(f["skills"])
    assert f["email"] == "ivan@mail.ru" and f["experience_years"] == 3 and f["specialization_guess"] == "backend"
    bad = client.post("/api/candidate/resume/parse", files={"file": ("x.pdf", b"hello", "application/pdf")}, headers=hc)
    assert bad.status_code == 400
