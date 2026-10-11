# API

Единственный API для интерфейса — `/api/...` основного FastAPI. Swagger: http://localhost:8000/docs. JSON-схема при запуске: http://localhost:8000/openapi.json. В `docs/openapi.json` сохранён снимок схемы этой сборки.

Авторизация: `POST /api/auth/login`; далее `Authorization: Bearer <access_token>`. Роль проверяет бэкенд. Основные группы маршрутов: auth, candidate, employer, testing, invitations, vacancies, applications, short tasks, FSP и ATS. Точные тела и ответы проверяйте по схеме, а не по API автономных прототипов.

Новое в тестировании: `POST /api/testing/attempts/{id}/check` с `{"item_id":"q1","code":"def solve(...): ..."}`. Ответ содержит `passed`, `total`, `checks_used`, `checks_remaining`, `check_limit` и безопасные сообщения. Публичные задания содержат `difficulty`, `base_weight`, `bonus_weight`, `max_score` и счётчик проверок. Скрытые тесты и правильные ответы не возвращаются.

Загрузка PDF: `POST /api/candidate/resume/parse`, multipart-файл. Для GigaChat следует предусмотреть ожидание до 20 секунд и запас по таймауту интерфейса. `source` указывает ml/fallback. Все обращения идут через бэкенд.

`GET /api/health` сообщает статус, окружение, версию и `build` (отпечаток кода и миграция). Отпечаток меняется после изменения файлов; не сверяйте его со старым фиксированным значением из переписки.

[Таблица всех маршрутов](api_routes.md) автоматически обновляется командой `python -m scripts.export_api` из backend/. Обзор этого раздела при экспорте не перезаписывается.
