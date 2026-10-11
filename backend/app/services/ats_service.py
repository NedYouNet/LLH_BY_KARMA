"""
Интеграция с ATS работодателя (Applicant Tracking System: Хантфлоу, Talantix, Potok и т.п.).

ТЗ называет её «плюсом за рамками MVP» и ждёт концепцию; здесь — рабочий скелет этой концепции:

  1. Работодатель указывает адрес своей ATS (вебхук). Платформа выдаёт ему секрет — один раз.
  2. Когда кандидат ПРИНИМАЕТ приглашение (а значит, сам открыл контакты этой компании),
     платформа отправляет в ATS событие `invitation.accepted` с карточкой кандидата.
  3. Каждое событие подписано HMAC-SHA256 (заголовок X-FSP-Signature) — ATS проверяет, что письмо
     от нас и не подменено; X-FSP-Event-Id — чтобы ATS не создала дубль при повторе.
  4. Каждая отправка пишется в журнал ats_deliveries, а раскрытие контактов — в contact_access_log (152-ФЗ).

Безопасность: в продакшене принимаем только https и не ходим на внутренние адреса (защита от SSRF —
чтобы через «адрес ATS» нельзя было обратиться к нашей собственной сети).
Отправка идёт в фоне после ответа — медленная ATS не задерживает кандидата.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import time
import uuid
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import BadRequest, NotFound
from app.models import AtsDelivery, CandidateProfile, EmployerProfile, Invitation
from app.services.presenters import log_contact_access

TIMEOUT = 5.0
EVENTS = ["invitation.accepted", "ats.test"]


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise BadRequest("Адрес ATS должен начинаться с https://", "ATS_URL_INVALID",
                         extra={"fields": {"webhook_url": "Нужен адрес вида https://ats.example.ru/hooks/fsp"}})
    if settings.environment == "prod":
        if p.scheme != "https":
            raise BadRequest("В продакшене адрес ATS должен быть https://", "ATS_URL_INVALID",
                             extra={"fields": {"webhook_url": "Только https://"}})
        try:
            addrs = {ai[4][0] for ai in socket.getaddrinfo(p.hostname, p.port or 443)}
        except socket.gaierror:
            raise BadRequest("Не удалось найти такой адрес", "ATS_URL_INVALID",
                             extra={"fields": {"webhook_url": "Адрес не существует"}})
        for a in addrs:
            ip = ipaddress.ip_address(a)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise BadRequest("Адрес ATS ведёт во внутреннюю сеть — так нельзя", "ATS_URL_FORBIDDEN",
                                 extra={"fields": {"webhook_url": "Внутренние адреса запрещены"}})
    return url


def sign(secret: str, timestamp: str, body: bytes) -> str:
    """Подпись, которую ATS должна пересчитать и сравнить: HMAC-SHA256(secret, "<timestamp>.<тело>")."""
    return "sha256=" + hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def _post(url: str, body: bytes, headers: dict) -> httpx.Response:  # вынесено отдельно — подменяется в тестах
    return httpx.post(url, content=body, headers=headers, timeout=TIMEOUT, follow_redirects=False)


def deliver(session_factory: sessionmaker, employer_id: int, url: str, secret: str, event: str,
            payload: dict) -> AtsDelivery:
    """Отправляет событие и записывает результат. Ничего не выбрасывает: ATS недоступна — это не наша авария."""
    event_id = payload["event_id"]
    body = json.dumps(payload, ensure_ascii=False, default=str).encode()
    ts = str(int(time.time()))
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "FSP-Talent-Webhook/1.0",
               "X-FSP-Event": event, "X-FSP-Event-Id": event_id, "X-FSP-Timestamp": ts,
               "X-FSP-Signature": sign(secret, ts, body)}
    rec = AtsDelivery(employer_id=employer_id, event=event, event_id=event_id, url=url)
    try:
        r = _post(url, body, headers)
        rec.status_code, rec.ok = r.status_code, 200 <= r.status_code < 300
        if not rec.ok:
            rec.error = f"ATS ответила {r.status_code}"
    except httpx.HTTPError as e:
        rec.error = f"{type(e).__name__}: {e}"[:500]
    db = session_factory()
    try:
        db.add(rec)
        db.commit()
        db.refresh(rec)
    finally:
        db.close()
    return rec


def candidate_payload(c: CandidateProfile) -> dict:
    ach = c.fsp_achievements or []
    return {
        "platform_id": c.id,
        "full_name": c.full_name, "email": c.contact_email or (c.user.email if c.user else None),
        "phone": c.phone, "telegram": c.telegram, "city": c.city,
        "specialization": c.effective_specialization, "grade": c.effective_grade,
        "grade_verified": c.grade_verified, "test_score": c.test_score if c.grade_verified else None,
        "experience_years": c.experience_years, "skills": c.skills or [], "about": c.about,
        "fsp": {"fsp_id": c.fsp_id, "sport_rank": c.fsp_rank, "competitions": len(ach),
                "prizes": sum(1 for a in ach if a.get("place") in (1, 2, 3))} if c.fsp_id else None,
        "profile_url": f"{settings.frontend_url.rstrip('/')}/employer/candidates/{c.id}",
    }


class AtsService:
    def __init__(self, db: Session):
        self.db = db

    def _factory(self) -> sessionmaker:
        return sessionmaker(bind=self.db.get_bind(), autoflush=False, expire_on_commit=False)

    # ------------------------------------------------------------ настройка
    def config(self, e: EmployerProfile, secret: str | None = None) -> dict:
        deliveries = self.db.scalars(select(AtsDelivery).where(AtsDelivery.employer_id == e.id)
                                     .order_by(AtsDelivery.id.desc()).limit(10)).all()
        return {"enabled": bool(e.ats_webhook_url), "webhook_url": e.ats_webhook_url, "events": EVENTS,
                "secret": secret,
                "secret_hint": ("…" + e.ats_webhook_secret[-4:]) if e.ats_webhook_secret else None,
                "signature_header": "X-FSP-Signature: sha256=HMAC_SHA256(secret, X-FSP-Timestamp + '.' + тело)",
                "recent_deliveries": deliveries}

    def configure(self, e: EmployerProfile, webhook_url: str, rotate_secret: bool) -> dict:
        e.ats_webhook_url = _validate_url(webhook_url)
        new_secret = None
        if rotate_secret or not e.ats_webhook_secret:
            new_secret = "whsec_" + secrets.token_urlsafe(32)
            e.ats_webhook_secret = new_secret
        self.db.commit()
        return self.config(e, secret=new_secret)

    def disable(self, e: EmployerProfile) -> None:
        e.ats_webhook_url, e.ats_webhook_secret = None, None
        self.db.commit()

    def send_test(self, e: EmployerProfile) -> AtsDelivery:
        if not e.ats_webhook_url:
            raise NotFound("Интеграция с ATS не настроена", "ATS_NOT_CONFIGURED")
        payload = {"event": "ats.test", "event_id": uuid.uuid4().hex, "occurred_at": utcnow().isoformat(),
                   "platform": "fsp-talent", "message": "Проверка связи с платформой FSP Talent"}
        return deliver(self._factory(), e.id, e.ats_webhook_url, e.ats_webhook_secret, "ats.test", payload)

    # ------------------------------------------------------------ события
    def prepare_invitation_accepted(self, inv: Invitation):
        """
        Собирает событие сразу (данные расшифровываются в текущей сессии), а отправку возвращает
        как функцию без аргументов — её запускают в фоне. None — если у компании нет ATS.
        """
        e = inv.employer
        if not e or not e.ats_webhook_url or not e.ats_webhook_secret:
            return None
        c = inv.candidate
        payload = {
            "event": "invitation.accepted", "event_id": uuid.uuid4().hex, "occurred_at": utcnow().isoformat(),
            "platform": "fsp-talent",
            "invitation": {"id": inv.id, "position_title": inv.position_title, "vacancy_id": inv.vacancy_id,
                           "salary_from": inv.salary_from, "salary_to": inv.salary_to,
                           "salary_type": inv.salary_type, "currency": "RUB", "candidate_reply": inv.candidate_reply},
            "candidate": candidate_payload(c),
        }
        # Передача контактов в ATS — тоже раскрытие ПДн: фиксируем в журнале, который видит кандидат
        log_contact_access(self.db, e.id, c.id, f"ats_webhook:invitation:{inv.id}")
        self.db.commit()
        factory, url, secret, eid = self._factory(), e.ats_webhook_url, e.ats_webhook_secret, e.id
        return lambda: deliver(factory, eid, url, secret, "invitation.accepted", payload)
