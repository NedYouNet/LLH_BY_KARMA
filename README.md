# FSP Talent — платформа подбора ИТ-специалистов с верифицированным профилем ФСП

Хакатон «Лидеры цифровой трансформации 2026», команда LLH_BY_KARMA.

**Обратная механика найма.** Кандидаты проходят тест, и система раскладывает их по категориям
(«Бэкенд · Middle»). Работодатель сам ищет в категоризированной базе, видит объяснимую подборку
(«почему он») и отправляет адресное приглашение с обязательной вилкой зарплаты в рублях.
Контакты кандидата скрыты, пока он не примет приглашение. Достижения ФСП подтягиваются из FSP ID
и поднимают кандидата внутри его категории.

## Быстрый старт

```bash
docker compose up --build -d
docker compose exec backend python -m scripts.seed --reset
```

Сайт — http://localhost:5173 · Swagger — http://localhost:8000/docs · демо-почта — http://localhost:8025

| Вход | Логин | Пароль |
|---|---|---|
| Работодатель | `employer@demo.ru` | `demo12345` |
| Кандидат с тестом и ФСП | `candidate@demo.ru` | `demo12345` |
| Новый кандидат | `newbie@demo.ru` | `demo12345` |
| Через FSP ID (имитация) | `maria.fsp@demo.ru` | `fsp12345` |

Подробности — [docs/08_build_and_run.md](docs/08_build_and_run.md).

## Документация

| # | Раздел (обязательный перечень организаторов) |
|---|---|
| 1 | [Архитектура](docs/01_architecture.md) |
| 2 | [Механика тестирования](docs/02_testing_mechanics.md) |
| 3 | [Механика подбора и логика категоризации](docs/03_matching_and_categorization.md) |
| 4 | [Процедура валидации и её результаты](docs/04_validation.md) |
| 5 | [Схемы интеграции с ФСП и FSP ID (Keycloak)](docs/05_fsp_integration.md) |
| 6 | [Описание API](docs/06_api.md) · [openapi.json](docs/openapi.json) · Swagger на стенде |
| 7 | [Перечень библиотек с версиями](docs/07_libraries.md) |
| 8 | [Инструкция по сборке и запуску](docs/08_build_and_run.md) |
| + | [Безопасность и 152-ФЗ](docs/09_security_152fz.md) · [ATS и защита от фиктивных вакансий](docs/10_ats_and_trust.md) |

## Как выполнены требования ТЗ

| Требование | Где |
|---|---|
| Кабинеты кандидата и работодателя | `backend/app/api/routers/candidate.py`, `employer.py`, фронтенд |
| Регистрация по email с подтверждением | `POST /api/auth/register` → письмо → `/verify-email` |
| Профиль и резюме: форма или PDF с автораспознаванием, PDF-профиль | `/api/candidate/resume/parse` (ML-модель + запасной парсер), `/api/candidate/profile/pdf` |
| Тест присваивает грейд, категоризация автоматическая | [docs/02](docs/02_testing_mechanics.md): план 5/3/2, порог 70%, кулдауны |
| Уникальные задания (ответы не расходятся между кандидатами) | Параметризованные шаблоны; утёкший ключ даёт 31% вместо 100% ([docs/04](docs/04_validation.md)) |
| Объяснимый подбор, адресное приглашение | `reasons` + `breakdown` в каждой карточке ([docs/03](docs/03_matching_and_categorization.md)) |
| Вилка ЗП в рублях обязательна | В вакансии и в приглашении, с пометкой gross/net |
| Контакты скрыты до согласия кандидата | `services/presenters.py`, проверка на сервере, журнал раскрытий, отзыв доступа |
| Связь профиля с FSP ID, Keycloak-совместимость | Вход через FSP ID по OpenID Connect + имитация реалма ([docs/05](docs/05_fsp_integration.md)) |
| Корректная обработка кандидата без истории ФСП | В выдаче без бонуса, с понятной плашкой; покрыто автотестами |
| Своя процедура валидации с результатами | `python -m scripts.evaluate` ([docs/04](docs/04_validation.md)) |
| Десятки одновременных пользователей | `python -m scripts.load_test`: 50 пользователей, 0 ошибок ([docs/04](docs/04_validation.md)) |
| 152-ФЗ, роли, безопасное хранение паролей и токенов | [docs/09](docs/09_security_152fz.md): AES-256-GCM для ПДн, scrypt, ротация токенов |
| OpenAPI | Swagger `/docs`, [docs/06](docs/06_api.md) |

## Структура

```
backend/            API: FastAPI + PostgreSQL (README внутри); ML-часть — backend/app/ml
frontend/           веб-интерфейс: React + Vite
docs/               документация
docker-compose.yml  запуск всего проекта одной командой
```
