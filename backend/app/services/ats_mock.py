"""
Встроенный ТЕСТОВЫЙ приёмник вебхуков — имитация ATS работодателя (как имитация FSP ID).

Зачем: показать интеграцию с ATS вживую без настоящей ATS, без интернета и без HTTPS-адреса.
Работодатель указывает в настройках ATS адрес  http://localhost:8000/api/mock-ats/webhook,
нажимает «Отправить тестовое событие» (или кандидат принимает приглашение), и событие появляется
в GET /api/mock-ats/events с отметкой, что подпись проверена.

Приёмник ведёт себя как добросовестная ATS:
  - проверяет подпись X-FSP-Signature = sha256=HMAC_SHA256(секрет, X-FSP-Timestamp + "." + тело);
  - отклоняет устаревшие события (больше 5 минут) — защита от повторной отправки перехваченного;
  - не создаёт дубль, если то же событие (X-FSP-Event-Id) пришло ещё раз — идемпотентность.
В продакшене выключен (404): там события уходят в настоящую ATS работодателя.
"""
import hmac
import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequest, NotFound, Unauthorized
from app.models import EmployerProfile, MockAtsEvent
from app.services.ats_service import sign

MOCK_PATH = "/api/mock-ats/webhook"
MAX_AGE_SECONDS = 300


def mock_url() -> str:
    """Адрес приёмника, который указывается в настройках ATS. localhost — потому что бэкенд шлёт сам себе."""
    return f"http://localhost:8000{MOCK_PATH}"


class MockAtsService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _ensure_enabled() -> None:
        if settings.environment == "prod":
            raise NotFound("Тестовый приёмник ATS доступен только на демо-стенде")

    def receive(self, body: bytes, headers) -> dict:
        self._ensure_enabled()
        ts, signature = headers.get("X-FSP-Timestamp", ""), headers.get("X-FSP-Signature", "")
        event, event_id = headers.get("X-FSP-Event", ""), headers.get("X-FSP-Event-Id", "")
        if not (ts.isdigit() and signature and event and event_id):
            raise BadRequest("Не хватает заголовков X-FSP-*", "WEBHOOK_HEADERS_MISSING")
        if abs(time.time() - int(ts)) > MAX_AGE_SECONDS:
            raise Unauthorized("Событие устарело — возможна повторная отправка перехваченного", "WEBHOOK_EXPIRED")

        # Чей это секрет? Проверяем подпись секретами компаний, у которых ATS направлена в этот приёмник
        employers = self.db.scalars(select(EmployerProfile).where(
            EmployerProfile.ats_webhook_url.like(f"%{MOCK_PATH}%"))).all()
        owner = next((e for e in employers if e.ats_webhook_secret and hmac.compare_digest(
            sign(e.ats_webhook_secret, ts, body).encode(), signature.encode())), None)
        if owner is None:
            raise Unauthorized("Подпись не сошлась: событие не от платформы или изменено", "SIGNATURE_INVALID")

        if self.db.scalar(select(MockAtsEvent).where(MockAtsEvent.event_id == event_id)):
            return {"received": True, "duplicate": True, "event_id": event_id, "signature_valid": True}
        self.db.add(MockAtsEvent(employer_id=owner.id, event=event, event_id=event_id, signature_valid=True,
                                 payload=body.decode("utf-8", errors="replace")))
        self.db.commit()
        return {"received": True, "duplicate": False, "event_id": event_id, "signature_valid": True}

    def events(self, e: EmployerProfile, limit: int = 20) -> list[dict]:
        self._ensure_enabled()
        rows = self.db.scalars(select(MockAtsEvent).where(MockAtsEvent.employer_id == e.id)
                               .order_by(MockAtsEvent.id.desc()).limit(limit)).all()
        out = []
        for r in rows:
            try:
                payload = json.loads(r.payload) if r.payload else None
            except ValueError:
                payload = None
            out.append({"id": r.id, "event": r.event, "event_id": r.event_id,
                        "signature_valid": r.signature_valid, "received_at": r.received_at, "payload": payload})
        return out
