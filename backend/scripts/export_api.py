"""
Выгружает описание API для документации: docs/openapi.json и таблицу эндпоинтов в docs/06_api.md.

    python -m scripts.export_api

Запускать после изменений API: документация не разойдётся с кодом, её генерирует сам FastAPI.
"""
import json
from collections import defaultdict
from pathlib import Path

from app.main import app

DOCS = Path(__file__).resolve().parents[2] / "docs"

HEADER = """# 6. Описание API

Все методы описаны спецификацией **OpenAPI 3.1**, её генерирует сам код, поэтому документация не расходится
с реализацией:

- интерактивно (можно нажимать и пробовать): **http://localhost:8000/docs** (Swagger) и `/redoc`;
- файлом: [`docs/openapi.json`](openapi.json). Из него можно сгенерировать клиент или типы TypeScript.

## Общие правила

| Что | Как |
|---|---|
| Адрес | Все методы под префиксом `/api` |
| Авторизация | `Authorization: Bearer <access_token>`. Токен живёт 15 минут, обновляется через `POST /api/auth/refresh` (refresh-токен одноразовый, с ротацией) |
| Роли | `candidate`, `employer`. Роль берётся только из токена. Чужой объект = 404, не та роль = 403 `ROLE_REQUIRED` |
| Формат данных | JSON, имена полей в `snake_case`, даты в ISO 8601 (UTC), деньги — целые рубли в месяц |
| Ошибки | Всегда `{"code": "МАШИННЫЙ_КОД", "message": "текст для пользователя", "detail": "…"}`; у 422 ещё `fields: {поле: что не так}`; у 429 — `retry_after` и заголовок `Retry-After` |
| Пагинация | `page`, `page_size` (или `size`) → `{total, page, size, items}` |
| Скорость | Каждый ответ содержит заголовок `X-Process-Time-Ms` |

Основные коды ошибок: `EMAIL_TAKEN`, `EMAIL_NOT_VERIFIED`, `INVALID_CREDENTIALS`, `ACCOUNT_TEMPORARILY_LOCKED`,
`TOKEN_EXPIRED`, `TOKEN_REUSED`, `ROLE_REQUIRED`, `SURVEY_REQUIRED`, `ATTEMPT_IN_PROGRESS`, `GRADE_COOLDOWN`,
`RETRY_COOLDOWN`, `INVITATION_EXISTS`, `INVALID_STATUS_TRANSITION`, `COMPANY_PROFILE_INCOMPLETE`,
`CONTACT_REQUIRED`, `ALREADY_APPLIED`, `FSP_NOT_FOUND`, `FSP_ID_TAKEN`, `FSP_ID_*` (вход через FSP ID),
`ATS_URL_INVALID`, `CONSENT_REQUIRED`, `VALIDATION_ERROR`, `NOT_FOUND`.

## Ключевые сценарии

| Сценарий | Запросы |
|---|---|
| Регистрация по почте | `POST /auth/register` → письмо → `POST /auth/verify-email` → `POST /auth/login` |
| Вход через FSP ID | открыть в браузере `GET /auth/fsp-id/login` → страница FSP ID → `/auth/fsp-id/callback` → токены |
| Путь кандидата | `POST /candidate/survey` → `PUT /candidate/consents` → `POST /testing/attempts` → `POST /testing/attempts/{id}/submit` |
| Подбор | `POST /employer/needs` (или вакансия) → `GET /candidates?needs_id=…` или `GET /vacancies/{id}/matches` |
| Приглашение | `POST /invitations` → кандидат `POST /invitations/{id}/accept` → работодатель `GET /candidates/{id}` (контакты открыты) |
| Отзыв контактов | кандидат `PUT /invitations/{id}/contact-access {"granted": false}` |
| ATS | `PUT /employer/integrations/ats` → при принятии приглашения в ATS уходит `invitation.accepted` |
| 152-ФЗ | `GET /candidate/contact-access-log`, `GET /candidate/export`, `DELETE /candidate/account` |

## Все методы
"""


def main() -> None:
    spec = app.openapi()
    DOCS.mkdir(exist_ok=True)
    (DOCS / "openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    groups: dict[str, list] = defaultdict(list)
    n = 0
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            tag = (op.get("tags") or ["Прочее"])[0]
            lock = "🔒" if op.get("security") else ""
            groups[tag].append(f"| `{method.upper()}` | `{path}` | {op.get('summary', '')} | {lock} |")
            n += 1
    lines = [HEADER, f"Всего: **{n}** методов (🔒 — нужен токен).\n"]
    for tag, rows in groups.items():
        lines += [f"\n### {tag}\n", "| Метод | Путь | Что делает | |", "|---|---|---|---|", *rows]
    (DOCS / "06_api.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"docs/openapi.json и docs/06_api.md обновлены: {n} методов")


if __name__ == "__main__":
    main()
