"""Механика тестирования: уникальность, скрытие ответов, грейды, кулдауны."""
from app.services.testing_engine import build_items
from app.testing_bank import TEMPLATES
from tests.conftest import SURVEY, correct_answer, pass_test, register


def test_bank_generates_valid_items():
    for t in TEMPLATES:
        import random
        for seed in range(30):
            v = t.make(random.Random(seed))
            assert v["text"]
            if t.kind == "single":
                assert v["answer"] in v["options"], t.id
            if t.kind == "code":
                assert v["code"]["tests"], t.id


def test_variants_differ_between_candidates_but_blueprint_is_same():
    a = build_items("backend", "middle", seed=1)
    b = build_items("backend", "middle", seed=2)
    assert sorted(i["level"] for i in a) == sorted(i["level"] for i in b)  # одинаковая сложность
    assert [i["text"] for i in a] != [i["text"] for i in b]  # разные варианты


def test_survey_required_before_test(client):
    h = register(client, "s@test.ru")
    r = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "junior"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "SURVEY_REQUIRED"


def test_answers_never_sent_to_frontend(client):
    h = register(client, "leak@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    r = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "middle"}, headers=h)
    body = r.json()
    for item in body["items"]:
        assert "answer" not in item
        if item["code"]:
            assert "tests" not in item["code"]


def test_pass_assigns_category(client, db):
    h = register(client, "p@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    res = pass_test(client, db, h, grade="junior")
    assert res["passed"] and res["decision"]["changed"] and res["decision"]["grade_after"] == "junior"
    st = client.get("/api/candidate/category", headers=h).json()
    assert st["category"] == "Бэкенд · Junior"


def test_fail_lower_retake_allowed_same_grade_blocked(client, db):
    h = register(client, "f@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    res = pass_test(client, db, h, grade="middle", target_score=30)
    assert not res["passed"] and res["decision"]["grade_after"] is None
    # тот же грейд сразу — нельзя
    r = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "middle"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "RETRY_COOLDOWN"
    # уровнем ниже — можно сразу
    assert pass_test(client, db, h, grade="junior")["passed"]


def test_grade_not_lowered_and_cooldown(client, db):
    h = register(client, "cd@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    res = pass_test(client, db, h, grade="junior", target_score=75)
    assert res["passed"] and not res["decision"]["upgrade_suggested"]
    # сдал без «уверенного» результата -> поднять грейд можно только через 90 дней
    r = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "middle"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "GRADE_COOLDOWN"


def test_confident_pass_allows_immediate_upgrade_and_fail_keeps_grade(client, db):
    h = register(client, "up@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    res = pass_test(client, db, h, grade="junior")
    assert res["score"] == 100 and res["decision"]["upgrade_suggested"]
    res2 = pass_test(client, db, h, grade="middle", target_score=20)  # провал на уровень выше
    assert not res2["passed"] and res2["decision"]["grade_after"] == "junior"  # грейд НЕ понижен


def test_code_item_checked_on_server(client, db):
    from app.models import TestAttempt
    h = register(client, "code@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h)
    attempt = None
    for grade in ("middle", "senior"):
        r = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": grade}, headers=h)
        attempt = db.get(TestAttempt, r.json()["id"])
        if any(i["kind"] == "code" for i in attempt.items):
            break
        client.post(f"/api/testing/attempts/{attempt.id}/submit", json={"answers": {}}, headers=h)
    code_item = next(i for i in attempt.items if i["kind"] == "code")
    answers = {i["id"]: correct_answer(i) for i in attempt.items}
    answers[code_item["id"]] = "import os\ndef solve(nums):\n    return os.listdir('/')"
    res = client.post(f"/api/testing/attempts/{attempt.id}/submit", json={"answers": answers}, headers=h).json()
    item = next(i for i in res["items"] if i["id"] == code_item["id"])
    assert item["status"] == "wrong" and any("os" in v for v in item["violations"])


def test_cannot_open_foreign_attempt(client, db):
    h1 = register(client, "x1@test.ru")
    client.post("/api/candidate/survey", json=SURVEY, headers=h1)
    aid = client.post("/api/testing/attempts", json={"specialization": "backend", "target_grade": "junior"},
                      headers=h1).json()["id"]
    h2 = register(client, "x2@test.ru")
    assert client.get(f"/api/testing/attempts/{aid}", headers=h2).status_code == 404
