# 8. Инструкция по сборке и запуску

## Что нужно

- **Docker** с Docker Compose v2 (Docker Desktop на Windows/macOS или Docker Engine на Linux).
- Свободные порты: 8000 (API), 5173 (сайт), 5432 (PostgreSQL), 8025 (почта).
- Ориентир по ресурсам: 2+ CPU, 2+ ГБ RAM, без видеокарты.

## Запуск (одна команда + демо-данные)

```bash
git clone <ссылка на репозиторий> && cd LLH_BY_KARMA
docker compose up --build -d                                  # первый раз 3–10 минут
docker compose exec backend python -m scripts.seed --reset    # демо-данные: 200 кандидатов, 6 компаний, 20 вакансий
```

При старте бэкенд сам применяет миграции базы данных (`alembic upgrade head`).

| Что | Адрес |
|---|---|
| Сайт | http://localhost:5173 |
| Документация API (Swagger) | http://localhost:8000/docs |
| Демо-почта (письма подтверждения) | http://localhost:8025 |
| Проверка, что сервер жив | http://localhost:8000/api/health |

## Демо-доступы

| Вход | Логин | Пароль |
|---|---|---|
| Работодатель «ООО Цифровые Решения» (с вакансиями) | `employer@demo.ru` | `demo12345` |
| Кандидат с тестом, ФСП и входящим приглашением | `candidate@demo.ru` | `demo12345` |
| Новый кандидат (пройти путь с нуля: анкета → тест) | `newbie@demo.ru` | `demo12345` |
| Ещё работодатели | `hr1@demo.ru` … `hr5@demo.ru` | `demo12345` |
| Вход через FSP ID (имитация) | `maria.fsp@demo.ru`, `olga.fsp@demo.ru`, `ivan.fsp@demo.ru`, `candidate@demo.ru` | `fsp12345` |

Жюри может зарегистрироваться с нуля: письмо подтверждения придёт в демо-почту (http://localhost:8025).

## Настройки

Все настройки задаются переменными окружения (или файлом `.env` в корне рядом с `docker-compose.yml`).
Полный список с пояснениями — `backend/.env.example`. Важное для стенда:

| Переменная | По умолчанию | Зачем |
|---|---|---|
| `WEB_CONCURRENCY` | 4 | Число процессов бэкенда. На 8 CPU — 8 |
| `DATA_ENCRYPTION_KEYS` | dev-ключ | Ключ шифрования ПДн. Сгенерировать: `docker compose exec backend python -m scripts.encryption gen-key` |
| `JWT_SECRET` | dev-секрет | Секрет подписи токенов (32+ символа) |
| `FSP_ID_MODE` | `mock` | `mock` — имитация FSP ID, `oidc` — настоящий Keycloak, `off` — без входа через FSP ID |
| `TEST_QUESTIONS_COUNT` | 10 | Длина теста. Для экспресс-проверки можно 6 |
| `ENVIRONMENT` | `dev` | `prod` — строгий режим: сервер не стартует с дефолтными секретами и `CORS=*` |

## Проверки

```bash
docker compose exec backend python -m scripts.evaluate          # валидация тестирования и подбора (раздел 4)
docker compose exec backend python -m scripts.load_test --url http://localhost:8000   # нагрузка
docker compose exec backend python -m scripts.encryption check  # в БД нет открытых персональных данных
docker compose exec backend python -m scripts.fsp_data check    # проверка таблицы реальных результатов ФСП
```

Автотесты запускаются без Docker:
```bash
cd backend
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q                                           # 78 тестов, SQLite в памяти
```
Они же автоматически прогоняются в GitHub Actions на каждый push (SQLite и PostgreSQL).

## Остановка и сброс

```bash
docker compose down        # остановить (данные сохраняются)
docker compose down -v     # остановить и удалить базу (полный сброс)
```

## Частые проблемы

| Симптом | Решение |
|---|---|
| `port is already allocated` | Порт занят другой программой: остановите её или поменяйте левую часть порта в `docker-compose.yml` |
| Пустые списки кандидатов | Не залиты демо-данные: команда `seed --reset` выше |
| Бэкенд перезапускается в цикле | `docker compose logs backend`: чаще всего не поднялась база или в `.env` ошибка |
