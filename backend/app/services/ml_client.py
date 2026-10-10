"""
Разбор резюме: ML-модель участника 3 + запасной парсер.

Порядок:
  1. ML внутри бэкенда: app/ml/resume.py -> parse_resume(...)   (если ENABLED = True);
  2. ML отдельным сервисом: POST {ML_SERVICE_URL}/api/cv/parse  (если адрес задан; контакты маскируются);
  3. встроенный простой парсер (pypdf + правила).
Правило надёжности: ошибка или «не смог» на любом шаге — НЕ падаем, а идём к следующему.
"""
import io
import logging
import re

import httpx
from pypdf import PdfReader

from app.core.config import settings
from app.reference import ALL_SKILLS, GRADE_CODES, SKILLS, SOFT_SKILLS, TEAM_ROLES

log = logging.getLogger("ml")


def parse_resume_in_process(pdf_bytes: bytes, text: str, filename: str) -> dict | None:
    from app.ml import resume as ml_resume
    if not ml_resume.ENABLED:
        return None
    try:
        data = ml_resume.parse_resume(pdf_bytes, text, filename)
        return data if isinstance(data, dict) and data else None
    except Exception as e:  # ошибка модели не должна ронять загрузку резюме
        log.warning("ML-разбор резюме упал, используем встроенный парсер: %s", e)
        return None


def _mask_contacts(text: str) -> str:
    """152-ФЗ, минимизация: во внешнюю модель не уходят почта, телефон и Telegram (их бэкенд находит сам)."""
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[телефон]", text)
    return _TG.sub("[telegram]", text)


def _from_ml_service(data: dict, text: str) -> dict:
    """Ответ ML-сервиса ({full_name, grade, skills, experience_years}) -> наш ParsedResume.
    База — встроенный парсер (контакты, город, soft skills), поверх — то, что уверенно вернула модель."""
    out = fallback_parse(text)
    name = data.get("full_name")
    if isinstance(name, str) and name.strip() and name.strip().lower() not in ("не указано", "unknown", "none"):
        out["full_name"] = name.strip()
    grade = str(data.get("grade") or "").strip().lower()
    if grade in GRADE_CODES:
        out["grade_guess"] = grade
    canon = {s.lower(): s for s in ALL_SKILLS}
    skills = [canon.get(str(s).strip().lower(), str(s).strip()) for s in (data.get("skills") or []) if str(s).strip()]
    if skills:
        out["skills"] = list(dict.fromkeys([*skills, *out["skills"]]))[:40]
        spec_scores = {spec: sum(1 for s in lst if s in out["skills"]) for spec, lst in SKILLS.items()}
        if any(spec_scores.values()):
            out["specialization_guess"] = max(spec_scores, key=spec_scores.get)
    exp = data.get("experience_years")
    if isinstance(exp, (int, float)) and 0 <= exp <= 60:
        out["experience_years"] = float(exp)
    return out


def parse_resume_via_ml(text: str) -> dict | None:
    """ML-сервис участника 3 (FastAPI + GigaChat): POST {ML_SERVICE_URL}/api/cv/parse {"cv_text": ...}."""
    if not settings.ml_service_url or not text.strip():
        return None
    try:
        r = httpx.post(f"{settings.ml_service_url.rstrip('/')}/api/cv/parse",
                       json={"cv_text": _mask_contacts(text)[:15000]}, timeout=settings.ml_timeout_seconds)
        r.raise_for_status()
        data = r.json()
        return _from_ml_service(data, text) if isinstance(data, dict) else None
    except (httpx.HTTPError, ValueError) as e:  # нет токена GigaChat (500), «мусор» от LLM (502), сервис не запущен
        log.warning("ML-сервис недоступен, используем встроенный парсер: %s", e)
        return None


def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:10])
    except Exception:  # noqa: BLE001 — битый PDF не должен ронять сервер
        return ""


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
_TG = re.compile(r"(?:t\.me/|telegram[:\s]*|tg[:\s]*)@?([A-Za-z0-9_]{4,})", re.IGNORECASE)
_EXP = re.compile(r"(?:опыт[^\d\n]{0,25}|experience[^\d\n]{0,15})(\d{1,2}(?:[.,]\d)?)\s*(?:год|лет|года|years?)", re.IGNORECASE)
_NAME = re.compile(r"^\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*$", re.MULTILINE)
_CITY = re.compile(r"(?:город|г\.|city)[:\s]+([А-ЯЁA-Z][а-яёa-z-]+)", re.IGNORECASE)


def fallback_parse(text: str) -> dict:
    """Простой парсер на регулярных выражениях и словаре навыков."""
    low = text.lower()

    def has(word: str) -> bool:
        return re.search(r"(?<![\w])" + re.escape(word.lower()) + r"(?![\w])", low) is not None

    skills = [s for s in ALL_SKILLS if has(s)]
    spec_scores = {spec: sum(1 for s in lst if s in skills) for spec, lst in SKILLS.items()}
    spec_guess = max(spec_scores, key=spec_scores.get) if any(spec_scores.values()) else None
    exp = _EXP.search(text)
    exp_years = float(exp.group(1).replace(",", ".")) if exp else None
    grade_guess = None
    for g in ("senior", "middle", "junior", "intern"):
        if has(g):
            grade_guess = g
            break
    if grade_guess is None and exp_years is not None:
        grade_guess = "intern" if exp_years < 0.5 else "junior" if exp_years < 2 else "middle" if exp_years < 4 else "senior"
    name = _NAME.search(text)
    city = _CITY.search(text)
    tg = _TG.search(text)
    phone = _PHONE.search(text)
    email = _EMAIL.search(text)
    return {
        "full_name": name.group(1) if name else None,
        "email": email.group(0) if email else None,
        "phone": re.sub(r"[^\d+]", "", phone.group(0)) if phone else None,
        "telegram": "@" + tg.group(1) if tg else None,
        "city": city.group(1) if city else None,
        "skills": skills,
        "soft_skills": [s for s in SOFT_SKILLS if s.lower() in low],
        "team_roles": [r for r in TEAM_ROLES if r.lower() in low],
        "experience_years": exp_years,
        "specialization_guess": spec_guess,
        "grade_guess": grade_guess,
        "about": text.strip()[:600] or None,
    }
