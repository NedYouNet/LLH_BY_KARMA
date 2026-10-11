# Бэкенд ФСП Таланты

FastAPI и PostgreSQL; миграции Alembic. Общая инструкция — [README](../README.md), документация — [docs](../docs/08_build_and_run.md), изменения — [backend.txt](../docs/handoff/backend.txt).

Из корня запускайте `docker compose up -d --build`. Для первой демо-инициализации — `docker compose exec backend python -m scripts.seed` без reset. API: localhost:8000/docs. ML встроен; ключ не нужен для тестирования.

Локальные проверки с Python 3.12: установить `requirements-dev.txt`, выполнить `python -m pytest -q` и `python -m scripts.verify_hybrid_testing`. Тесты SQLite используют временную базу; PostgreSQL-прогон дополнительно выполняется в CI.
