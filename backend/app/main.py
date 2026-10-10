"""
Точка входа приложения.

Запуск локально:   uvicorn app.main:app --reload
Документация API:  http://localhost:8000/docs   (Swagger)
                   http://localhost:8000/redoc  (ReDoc)
"""
import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (auth, candidate, employer, fsp, fsp_id, invitations, mock_ats, reference, short_tasks,
                             testing, vacancies)
from app.core.buildinfo import applied_migration, code_fingerprint
from app.core.config import check_production_settings, settings
from app.core.crypto import get_cipher
from app.core.errors import AppError, app_error_handler, validation_error_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DESCRIPTION = """
**FSP Talent** — платформа подбора ИТ-специалистов с обратной механикой:
работодатель сам находит кандидата в категоризированной базе и отправляет приглашение с вилкой ЗП.

### Как авторизоваться в Swagger
1. `POST /api/auth/register` → `POST /api/auth/verify-email` (в dev-режиме токен приходит в ответе регистрации).
2. Кнопка **Authorize** вверху: username = email, password = пароль.

### Формат ошибок
`{"code": "MACHINE_CODE", "message": "текст для пользователя", "detail": "..."}`, для 422 ещё `fields: {поле: ошибка}`
"""

_problems = check_production_settings(settings)
if _problems:  # в продакшене с небезопасными настройками сервер не стартует
    raise RuntimeError("Небезопасная конфигурация: " + "; ".join(_problems))
get_cipher()  # проверяем ключи шифрования при старте, а не при первом запросе

# Версия бэкенда: видна в Swagger и в /api/health — по ней сразу понятно, свежий ли контейнер запущен
API_VERSION = "1.4.0"

app = FastAPI(title=settings.app_name, version=API_VERSION, description=DESCRIPTION,
              docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Заголовки безопасности для каждого ответа:
      nosniff — браузер не «угадывает» тип файла; DENY — API нельзя встроить во фрейм (кликджекинг);
      no-store — ответы с персональными данными не кэшируются браузером и прокси;
      HSTS — браузер ходит только по HTTPS (включается в продакшене за HTTPS).
    """
    response = await call_next(request)
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "no-referrer"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith(settings.api_prefix):
        h["Cache-Control"] = "no-store"
        h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if settings.environment == "prod":
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def timing_header(request: Request, call_next):
    """Добавляет заголовок X-Process-Time — удобно показывать жюри скорость ответа."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
    return response


for r in (auth.router, fsp_id.router, reference.router, candidate.router, testing.router, employer.router,
          employer.ats_router, invitations.router, vacancies.router, short_tasks.router, fsp.router,
          fsp_id.mock_router, mock_ats.router):
    app.include_router(r, prefix=settings.api_prefix)


@app.get("/api/health", tags=["Служебное"], summary="Проверка, что сервис жив и какой код запущен")
def health():
    """`build.code` — отпечаток кода (свежая ли сборка), `build.migration` — применённая миграция БД."""
    from app.core.database import engine
    return {"status": "ok", "env": settings.environment, "version": API_VERSION,
            "build": {"code": code_fingerprint(), "migration": applied_migration(engine)},
            "features": ["employer_needs", "fsp_id_login", "ats_webhooks", "unverified_grades", "ml_in_process",
                         "mock_ats_receiver"]}
