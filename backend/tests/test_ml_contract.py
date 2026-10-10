"""
Контракт с ML-частью (app/ml). Эти тесты — для участника 3: если они зелёные, его код встроен правильно.
    pytest -q tests/test_ml_contract.py
"""
import io

from app.ml import matching as ml_matching
from app.ml import resume as ml_resume
from app.services.matching_engine import SearchCriteria, rank
from tests.conftest import ready_candidate, register


def _pdf() -> bytes:
    from reportlab.pdfgen import canvas
    from app.services import pdf_service  # регистрирует шрифт с кириллицей
    buf = io.BytesIO()
    cv = canvas.Canvas(buf)
    cv.setFont(pdf_service._FONT, 12)
    cv.drawString(50, 800, "Иван Петров ivan@mail.ru Python FastAPI")
    cv.save()
    return buf.getvalue()


def _parse(client, email="cv@test.ru"):
    h = register(client, email)
    return client.post("/api/candidate/resume/parse", files={"file": ("cv.pdf", _pdf(), "application/pdf")},
                       headers=h).json()


def test_ml_resume_parser_is_used_when_enabled(client, monkeypatch):
    seen = {}

    def fake(pdf_bytes, text, filename):
        seen.update(text=text, filename=filename, is_pdf=pdf_bytes.startswith(b"%PDF"))
        return {"full_name": "Иван Петров", "skills": ["Python"], "grade_guess": "middle", "лишнее": 1}
    monkeypatch.setattr(ml_resume, "ENABLED", True)
    monkeypatch.setattr(ml_resume, "parse_resume", fake)
    out = _parse(client)
    assert out["source"] == "ml" and out["fields"]["grade_guess"] == "middle"
    assert seen["is_pdf"] and seen["filename"] == "cv.pdf" and "Python" in seen["text"]


def test_ml_failure_falls_back_to_builtin_parser(client, monkeypatch):
    def broken(*_):
        raise RuntimeError("модель не загрузилась")
    monkeypatch.setattr(ml_resume, "ENABLED", True)
    monkeypatch.setattr(ml_resume, "parse_resume", broken)
    out = _parse(client)
    assert out["source"] == "fallback" and "Python" in out["fields"]["skills"]


def test_ml_text_similarity_plugs_into_ranking(client, db, monkeypatch):
    from app.models import CandidateProfile
    ready_candidate(client, db)
    c = db.query(CandidateProfile).first()
    crit = SearchCriteria(specialization="backend", skills=["Python"], text="Платёжный сервис на Python")
    monkeypatch.setattr(ml_matching, "ENABLED", True)
    monkeypatch.setattr(ml_matching, "text_similarity", lambda q, d: 0.9)
    (_, m), = rank([c], crit)
    assert m.breakdown["text"]["value"] == 0.9
    monkeypatch.setattr(ml_matching, "text_similarity", lambda q, d: 1 / 0)  # ошибка ML — компонента просто выпадает
    (_, m), = rank([c], crit)
    assert "text" not in m.breakdown and m.score > 0


def test_ml_service_contract_cv_parse(client, monkeypatch):
    """Отдельный ML-сервис (POST /api/cv/parse, GigaChat): ответ маппится в профиль, контакты в LLM не уходят."""
    import httpx
    from app.core.config import settings
    from app.services import ml_client
    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"full_name": "Не указано", "grade": "Middle", "skills": ["python", "FastAPI", "Docker"],
                    "experience_years": 3}

    def fake_post(url, json=None, timeout=None, **_):
        sent.update(url=url, text=json["cv_text"])
        return Resp()
    monkeypatch.setattr(settings, "ml_service_url", "http://ml:8000/")
    monkeypatch.setattr(ml_client.httpx, "post", fake_post)
    out = _parse(client)
    f = out["fields"]
    assert out["source"] == "ml" and sent["url"] == "http://ml:8000/api/cv/parse"
    assert "ivan@mail.ru" not in sent["text"] and "[email]" in sent["text"]  # 152-ФЗ: почта замаскирована
    assert f["grade_guess"] == "middle" and f["experience_years"] == 3.0 and f["specialization_guess"] == "backend"
    assert f["skills"][:3] == ["Python", "FastAPI", "Docker"]  # регистр приведён к справочнику
    assert f["full_name"] != "Не указано" and f["email"] == "ivan@mail.ru"  # заглушка модели не попадает в профиль

    def down(*_, **__):
        raise httpx.HTTPStatusError("502 LLM вернула мусор", request=None, response=None)
    monkeypatch.setattr(ml_client.httpx, "post", down)
    assert _parse(client, "cv2@test.ru")["source"] == "fallback"
