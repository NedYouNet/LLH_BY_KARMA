"""Разбор резюме через GigaChat."""
import json
import logging
import os

from app.reference import ALL_SKILLS, GRADE_CODES, SPEC_CODES
from app.services.ml_client import _mask_contacts

log = logging.getLogger("ml")
ENABLED = True

PROMPT = (
    "Ты HR-аналитик. Извлеки из резюме данные и верни ТОЛЬКО JSON без markdown-разметки: "
    '{"full_name": str|null, "skills": [str], "experience_years": float|null, '
    '"specialization_guess": один из ' + str(SPEC_CODES) + ', '
    '"grade_guess": один из ' + str(GRADE_CODES) + "}.\n\nРезюме:\n"
)

def parse_resume(pdf_bytes: bytes, text: str, filename: str) -> dict | None:
    token = os.environ.get("GIGA_TOKEN")
    # Демо обязано работать без ключа. Если его нет — бэкенд включит fallback
    if not token or not text.strip():
        return None

    try:
        from gigachat import GigaChat

        # Маскируем ПДн (почта, телефон, тг) по требованию 152-ФЗ
        safe_text = _mask_contacts(text)[:12000]

        # Низкая температура для аналитики, таймаут 15с (требование до 20с)
        with GigaChat(credentials=token, verify_ssl_certs=False, timeout=15,
                      model=os.environ.get("GIGA_MODEL", "GigaChat-Pro")) as giga:
            answer = giga.chat(PROMPT + safe_text).choices[0].message.content

        # Защита от лишнего текста вокруг JSON
        clean_json = answer[answer.find("{"): answer.rfind("}") + 1]
        data = json.loads(clean_json)

        canon = {s.lower(): s for s in ALL_SKILLS}
        out = {
            "full_name": data.get("full_name") or None,
            "skills": [canon.get(str(s).lower(), str(s)) for s in data.get("skills") or []],
            "experience_years": float(data.get("experience_years")) if data.get("experience_years") else None,
        }

        # Грейд должен быть строго маленькими буквами
        grade = str(data.get("grade_guess", "")).lower()
        if grade in GRADE_CODES:
            out["grade_guess"] = grade

        spec = str(data.get("specialization_guess", "")).lower()
        if spec in SPEC_CODES:
            out["specialization_guess"] = spec

        return out

    except Exception as e:
        log.error(f"Ошибка LLM-парсера: {e}")
        return None # При любой ошибке бэкенд возьмет встроенный парсер
