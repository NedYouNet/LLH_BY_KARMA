"""
Тестовый приёмник вебхуков — имитация ATS работодателя (только вне продакшена).

Как проверить интеграцию с ATS без настоящей ATS:
  1. PUT  /api/employer/integrations/ats  {"webhook_url": "http://localhost:8000/api/mock-ats/webhook"}
  2. POST /api/employer/integrations/ats/test   (или кандидат принимает приглашение)
  3. GET  /api/mock-ats/events  — что пришло, подпись проверена
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_employer
from app.core.errors import errors
from app.models import EmployerProfile
from app.schemas.employer import MockAtsEventOut, MockAtsReceipt
from app.services.ats_mock import MockAtsService

router = APIRouter(prefix="/mock-ats", tags=["Тестовый приёмник ATS (имитация)"])


@router.post("/webhook", response_model=MockAtsReceipt, responses=errors(400, 401, 404),
             summary="Принять событие платформы, как это сделала бы ATS (проверка подписи)")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Вызывает сама платформа. 401 — подпись не сошлась или событие старше 5 минут."""
    return MockAtsService(db).receive(await request.body(), request.headers)


@router.get("/events", response_model=list[MockAtsEventOut], responses=errors(401, 403, 404),
            summary="Работодатель: что получил тестовый приёмник (последние 20 событий)")
def events(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return MockAtsService(db).events(e)
