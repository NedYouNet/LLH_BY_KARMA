# FSP Talent — Backend

API платформы подбора ИТ-специалистов с обратной механикой: работодатель сам находит кандидата
в базе, разложенной по категориям по итогам тестирования, и отправляет ему приглашение с вилкой ЗП.

**Стек:** Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL 16 · Alembic · JWT (claims в формате Keycloak) · Docker

## Быстрый старт (Docker)

```bash
docker compose up --build                                   # из корня репозитория
docker compose exec backend python -m scripts.seed --reset  # демо-данные
```

| Что | Где |
|---|---|
| Swagger (документация API) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Почта (письма подтверждения) | http://localhost:8025 |

Демо-аккаунты (пароль `demo12345`): `candidate@demo.ru`, `newbie@demo.ru`, `employer@demo.ru`.
Вход через FSP ID (имитация, пароль `fsp12345`): `maria.fsp@demo.ru`, `olga.fsp@demo.ru`, `ivan.fsp@demo.ru`.

Полная документация для жюри — в папке [`docs/`](../docs) (архитектура, тестирование, подбор, валидация,
FSP ID, API, библиотеки, запуск, безопасность, ATS).

## Локальный запуск без Docker

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                     # Windows: copy .env.example .env
# нужен запущенный PostgreSQL с БД fsp (проще всего: docker compose up db)
alembic upgrade head                     # создать таблицы
python -m scripts.seed --reset           # демо-данные
uvicorn app.main:app --reload            # http://localhost:8000/docs
```

## Тесты и валидация

```bash
pytest -q                                # 78 автотестов API (SQLite в памяти)
TEST_DATABASE_URL=postgresql+psycopg://fsp:fsp@localhost:5432/fsp_test pytest -q   # на PostgreSQL
python -m scripts.evaluate               # процедура валидации -> scripts/output/evaluation.md
python -m scripts.load_test              # нагрузка на поднятом стенде (50 пользователей) -> scripts/output/load_test.md
python -m scripts.export_api             # обновить docs/openapi.json и docs/06_api.md
```

## Архитектура

```
app/
  main.py               точка входа, подключение роутеров, CORS, единый формат ошибок
  core/                 настройки (.env), БД, JWT и пароли, зависимости (кто вызывает и с какой ролью)
  models/               таблицы БД (SQLAlchemy)
  schemas/              Pydantic-схемы = контракт API для фронтенда
  repositories/         все SQL-запросы
  services/             бизнес-логика:
    testing_engine.py     генерация уникальных вариантов теста и подсчёт балла (чистые функции)
    code_runner.py        безопасная проверка кода кандидата (AST + отдельный процесс с лимитами)
    testing_service.py    правила грейдов: порог 70%, без понижения, кулдауны 90 дней и 24 часа
    matching_engine.py    ранжирование и объяснение выдачи (чистые функции)
    presenters.py         правила видимости: контакты только после принятия инвайта или отклика
    invitation_service.py машина состояний приглашений
    fsp_service.py        реестр ФСП: таблица реальных результатов + демо-реестр
    fsp_id_client.py      вход через FSP ID (OpenID Connect, Authorization Code + PKCE)
    fsp_id_mock.py        имитация FSP ID — Keycloak-реалма ФСП
    ats_service.py        отправка принятых кандидатов в ATS работодателя (подписанные вебхуки)
  api/routers/          HTTP-эндпоинты
  testing_bank/         банк параметризованных шаблонов заданий
alembic/                миграции БД
scripts/seed.py         демо-данные (200 кандидатов, 50 с ФСП, 20 вакансий)
scripts/evaluate.py     синтетическая валидация тестирования и подбора
tests/                  pytest
```

Слои: **Router → Service → Repository**. Роутер только принимает HTTP и отдаёт ответ,
сервис проверяет бизнес-правила, репозиторий ходит в БД.

## Формат ошибок

```json
{"code": "GRADE_COOLDOWN", "message": "Сменить грейд можно после 04.01.2027", "detail": "...", "next_change_at": "..."}
```

Коды: `EMAIL_TAKEN`, `EMAIL_NOT_VERIFIED`, `INVALID_CREDENTIALS`, `TOKEN_EXPIRED`, `ROLE_REQUIRED`,
`SURVEY_REQUIRED`, `ATTEMPT_IN_PROGRESS`, `GRADE_COOLDOWN`, `RETRY_COOLDOWN`, `INVITATION_EXISTS`,
`INVALID_STATUS_TRANSITION`, `ALREADY_APPLIED`, `FSP_NOT_FOUND`, `FSP_ID_TAKEN`, `CONSENT_REQUIRED`, `NOT_FOUND`.

## ML внутри бэкенда (участник 3)

Единый стек Python: ML-код живёт в `app/ml/` того же приложения (памятка: [`app/ml/README.md`](app/ml/README.md)).
Точки подключения: `app/ml/resume.py → parse_resume(pdf_bytes, text, filename)` (разбор резюме) и
`app/ml/matching.py → text_similarity(query, candidate_text)` (похожесть для ранжирования). Пока `ENABLED = False`,
работают встроенные варианты. Проверка контракта: `pytest -q tests/test_ml_contract.py`.

Если ML всё же вынесут в отдельный сервис, поддерживается и это: `POST {ML_SERVICE_URL}/parse`
(multipart, поле `file` — PDF) → `200`:

```json
{"full_name": "Иван Петров", "email": "ivan@mail.ru", "phone": "+79991234567", "telegram": "@ivan",
 "city": "Москва", "skills": ["Python", "FastAPI"], "soft_skills": [], "team_roles": [],
 "experience_years": 3, "specialization_guess": "backend", "grade_guess": "middle", "about": "..."}
```

Если ML не ответил или упал, бэкенд использует встроенный парсер (`services/ml_client.py`) — демо не упадёт.

## Реестр ФСП

Открытого API у ФСП нет, поэтому реестр собран из двух источников (`services/fsp_service.py`):

1. **Реальные результаты** из таблицы `data/fsp_results.xlsx` (или `.csv`), собранные вручную из открытых
   протоколов соревнований. Такие достижения помечаются `verification_status: "verified"` и содержат `source_url`.
2. **Демо-реестр** (если ID нет в таблице и `FSP_DEMO_FALLBACK=true`): ID из 6 цифр; оканчивается на `0` —
   участник без соревнований; иначе 1–5 достижений, одинаковых для одного ID. Помечаются `"demo"`.

```bash
python -m scripts.fsp_data template   # шаблон таблицы с инструкцией: data/fsp_results_template.xlsx
python -m scripts.fsp_data check      # проверить таблицу: число участников и строки с ошибками
python -m scripts.fsp_data sync       # обновить достижения у уже привязанных кандидатов
```

Файл подхватывается без перезапуска (в Docker папка `backend/data` подключена в контейнер).
ФИО и контакты в таблицу не вносятся — профиль связывается только по ID.
Для боевой интеграции достаточно реализовать `FspRegistryClient` поверх API ФСП — остальной код не меняется.

Ошибки валидации (422) дополнительно содержат `fields` — какое поле формы неверно:

```json
{"code": "VALIDATION_ERROR", "message": "Проверьте правильность заполнения полей",
 "fields": {"salary_to": "Зарплата «до» не может быть меньше зарплаты «от»"}, "detail": [...]}
```

## Безопасность и защита персональных данных (152-ФЗ)

| Угроза | Защита | Где в коде |
|---|---|---|
| Утечка базы данных (дамп, бэкап) | ПДн (ФИО, телефон, Telegram, email для связи, текст резюме, контакты HR) хранятся зашифрованными AES-256-GCM; ключи — только в переменной окружения, поддерживается ротация | `app/core/crypto.py`, `scripts/encryption.py` |
| Утечка паролей | scrypt + соль, политика стойкости (8+ символов, буквы и цифры, запрет словарных) | `app/core/security.py` |
| Перебор паролей | 20 попыток входа в минуту с IP, блокировка email на 15 минут после 5 неудач (429) | `app/core/rate_limit.py`, `services/auth_service.py` |
| Перебор email | Одинаковый ответ и одинаковое время ответа для «нет пользователя» и «неверный пароль» | `services/auth_service.py` |
| Кража токена | access 15 минут; refresh с ротацией; повторное использование старого refresh отзывает всю сессию; настоящий logout | `models/security.py`, `services/auth_service.py` |
| Доступ к чужим данным | Роль и пользователь — только из токена; чужие объекты = 404; контакты только после принятия инвайта/отклика | `core/deps.py`, `services/presenters.py` |
| Атаки через браузер | Заголовки nosniff, X-Frame-Options DENY, CSP, no-store, HSTS в продакшене | `app/main.py` |
| Небезопасный запуск | В `ENVIRONMENT=prod` сервер не стартует с дефолтным JWT-секретом, без ключа шифрования или с `CORS=*` | `core/config.py` |
| Права субъекта ПДн | Согласия с датой, приватность, журнал «кто видел мои контакты», выгрузка всех данных, удаление аккаунта | `services/privacy_service.py` |
| Расследование инцидентов | Журнал `auth_events`: входы, неудачи, блокировки, кражи токенов (email хранится как HMAC) | `models/security.py` |

```bash
python -m scripts.encryption gen-key   # новый ключ для DATA_ENCRYPTION_KEYS
python -m scripts.encryption check     # убедиться, что в БД нет открытых ПДн
python -m scripts.encryption rotate    # перешифровать всё новым ключом
```
