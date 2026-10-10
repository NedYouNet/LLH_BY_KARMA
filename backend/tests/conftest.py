"""
Общие фикстуры для тестов.

Тесты гоняются на SQLite в памяти — быстро и без PostgreSQL.
Чтобы прогнать на настоящем PostgreSQL:  TEST_DATABASE_URL=postgresql+psycopg://... pytest
"""
import os

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("EMAIL_VERIFICATION_REQUIRED", "true")
os.environ.setdefault("ML_SERVICE_URL", "")
os.environ.setdefault("SMTP_HOST", "")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")  # лимиты проверяются отдельно в test_security.py

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, enable_sqlite_fk, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app import models  # noqa: E402,F401  (регистрирует таблицы)

TEST_DB = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture()
def engine():
    if TEST_DB.startswith("sqlite"):
        eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        enable_sqlite_fk(eng)
    else:
        eng = create_engine(TEST_DB)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()  # закрыть соединения: иначе на PostgreSQL за прогон кончаются слоты подключений


@pytest.fixture()
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    fastapi_app.dependency_overrides[get_db] = override
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# ----------------------------- помощники -----------------------------
def register(client, email, role="candidate", password="Secure2026x", **extra) -> dict:
    """Регистрирует, подтверждает email, логинится. Возвращает заголовки авторизации."""
    body = {"email": email, "password": password, "role": role, **extra}
    if role == "employer":
        body.setdefault("company_name", "ООО Тест")
        if body["company_name"] == "":
            body.pop("company_name")
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    token = r.json()["dev_verification_token"]
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


SURVEY = {"industry": "fintech", "specialization": "backend", "experience_years": 2,
          "skills": ["Python", "PostgreSQL", "Docker"], "team_roles": ["Разработчик"], "work_format": "remote",
          "declared_grade": "junior"}


def correct_answer(item: dict) -> str:
    """Правильный ответ на задание, взятый из БД (на фронт он не уходит)."""
    if item["kind"] != "code":
        return item["answer"]
    table = {repr(t["args"][0]): t["expected"] for t in item["code"]["tests"]}
    return f"def {item['code']['function_name']}(nums):\n    table = {table!r}\n    return table[repr(nums)]\n"


def pass_test(client, db, headers, spec="backend", grade="junior", target_score: float | None = None) -> dict:
    """Проходит тест: все ответы верные или (target_score) — подбирает ответы, чтобы набрать ~нужный балл."""
    from app.models import TestAttempt
    r = client.post("/api/testing/attempts", json={"specialization": spec, "target_grade": grade}, headers=headers)
    assert r.status_code == 201, r.text
    attempt_id = r.json()["id"]
    db.expire_all()
    items = db.get(TestAttempt, attempt_id).items
    answers = {i["id"]: correct_answer(i) for i in items}
    if target_score is not None:
        total = sum(i["weight"] for i in items)
        got = total
        for i in sorted(items, key=lambda x: x["weight"]):  # убираем верные ответы, пока балл выше цели
            if 100 * (got - i["weight"]) / total >= target_score:
                answers[i["id"]] = "неверно"
                got -= i["weight"]
    r = client.post(f"/api/testing/attempts/{attempt_id}/submit", json={"answers": answers}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def ready_candidate(client, db, email="cand@test.ru", full_name="Иван Петров", **profile) -> dict:
    """Кандидат, прошедший весь обязательный путь и видимый работодателям."""
    h = register(client, email, full_name=full_name)
    client.patch("/api/candidate/profile", json={"phone": "+79990001122", "telegram": "@ivan", **profile}, headers=h)
    assert client.post("/api/candidate/survey", json=SURVEY, headers=h).status_code == 200
    res = pass_test(client, db, h)
    assert res["passed"], res
    r = client.put("/api/candidate/consents", json={"consent_processing": True, "consent_publication": True}, headers=h)
    assert r.status_code == 200
    return h
