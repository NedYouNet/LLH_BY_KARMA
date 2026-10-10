# 6. Описание API

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

Всего: **81** методов (🔒 — нужен токен).


### Авторизация

| Метод | Путь | Что делает | |
|---|---|---|---|
| `POST` | `/api/auth/register` | Регистрация кандидата или работодателя |  |
| `POST` | `/api/auth/verify-email` | Подтвердить email (токен из письма) |  |
| `POST` | `/api/auth/resend-verification` | Отправить письмо подтверждения ещё раз |  |
| `POST` | `/api/auth/login` | Вход (JSON) — для фронтенда |  |
| `POST` | `/api/auth/token` | Вход через форму — для кнопки Authorize в Swagger (username = email) |  |
| `POST` | `/api/auth/refresh` | Обновить пару токенов (ротация) |  |
| `POST` | `/api/auth/logout` | Выход (отзыв сессии) | 🔒 |
| `GET` | `/api/auth/me` | Кто я + чек-лист онбординга | 🔒 |
| `GET` | `/api/auth/fsp-id/config` | Показывать ли кнопку «Войти через FSP ID» |  |
| `GET` | `/api/auth/fsp-id/login` | Начать вход через FSP ID (переадресация на страницу FSP ID) |  |
| `GET` | `/api/auth/fsp-id/callback` | Сюда FSP ID возвращает пользователя после входа |  |

### Справочники

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/reference` | Все справочники одним запросом (кэшируйте на фронте) |  |

### Кандидат: профиль

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/candidate/profile` | Мой профиль | 🔒 |
| `PATCH` | `/api/candidate/profile` | Обновить профиль (только присланные поля) | 🔒 |
| `POST` | `/api/candidate/resume/parse` | Загрузить PDF-резюме и распознать поля | 🔒 |
| `GET` | `/api/candidate/profile/pdf` | Скачать стандартизированный PDF-профиль | 🔒 |
| `POST` | `/api/candidate/survey` | Шаг 1: анкета — IT-направление и грейд, на который претендую | 🔒 |
| `GET` | `/api/candidate/category` | Моя категория, грейд, когда можно менять, на какие грейды можно пройти тест | 🔒 |
| `PUT` | `/api/candidate/consents` | Согласия (152-ФЗ) | 🔒 |
| `PUT` | `/api/candidate/privacy` | Что видно работодателю | 🔒 |
| `POST` | `/api/candidate/fsp` | Привязать ФСП ID и подтянуть достижения из реестра | 🔒 |
| `DELETE` | `/api/candidate/fsp` | Отвязать ФСП ID | 🔒 |
| `GET` | `/api/candidate/contact-access-log` | Кто и когда получил доступ к моим контактам | 🔒 |
| `GET` | `/api/candidate/export` | Выгрузить все мои данные (JSON) | 🔒 |
| `DELETE` | `/api/candidate/account` | Удалить аккаунт и все мои данные | 🔒 |

### Кандидат: тестирование

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/testing/attempts` | История моих попыток | 🔒 |
| `POST` | `/api/testing/attempts` | Шаг 2–3: выбрать грейд и начать тест | 🔒 |
| `GET` | `/api/testing/attempts/{attempt_id}` | Получить попытку (например, после перезагрузки страницы) | 🔒 |
| `POST` | `/api/testing/attempts/{attempt_id}/submit` | Отправить ответы и получить результат + решение по грейду | 🔒 |
| `GET` | `/api/testing/attempts/{attempt_id}/result` | Результат завершённой попытки | 🔒 |

### Работодатель: подбор

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/employer/profile` | Профиль компании | 🔒 |
| `PATCH` | `/api/employer/profile` | Обновить профиль компании | 🔒 |
| `GET` | `/api/employer/needs` | Мои сохранённые потребности («кого ищем») | 🔒 |
| `POST` | `/api/employer/needs` | Сохранить новую потребность | 🔒 |
| `GET` | `/api/employer/needs/{need_id}` | Одна потребность | 🔒 |
| `PUT` | `/api/employer/needs/{need_id}` | Изменить потребность (присылается целиком) | 🔒 |
| `DELETE` | `/api/employer/needs/{need_id}` | Удалить потребность | 🔒 |
| `GET` | `/api/candidates` | Подборка через параметры адреса (удобно для фильтров на фронте) | 🔒 |
| `GET` | `/api/candidates/categories` | Обзор банка: категории и сколько в них кандидатов | 🔒 |
| `POST` | `/api/candidates/search` | Подборка: фильтры + ранжирование + обоснование каждого кандидата | 🔒 |
| `GET` | `/api/candidates/{candidate_id}` | Карточка кандидата (контакты — только после принятия инвайта/отклика) | 🔒 |
| `GET` | `/api/shortlist` | Избранные кандидаты | 🔒 |
| `POST` | `/api/shortlist` | Добавить в избранное | 🔒 |
| `DELETE` | `/api/shortlist/{candidate_id}` | Убрать из избранного | 🔒 |

### Работодатель: интеграция с ATS

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/employer/integrations/ats` | Настройки отправки кандидатов в вашу ATS и последние отправки | 🔒 |
| `PUT` | `/api/employer/integrations/ats` | Подключить ATS: адрес вебхука (секрет выдаётся один раз) | 🔒 |
| `DELETE` | `/api/employer/integrations/ats` | Отключить интеграцию с ATS | 🔒 |
| `POST` | `/api/employer/integrations/ats/test` | Отправить в ATS тестовое событие | 🔒 |

### Приглашения (главная механика)

| Метод | Путь | Что делает | |
|---|---|---|---|
| `POST` | `/api/invitations` | Работодатель: пригласить кандидата (вилка ЗП обязательна) | 🔒 |
| `GET` | `/api/invitations` | Мои приглашения: работодатель — отправленные, кандидат — входящие | 🔒 |
| `GET` | `/api/invitations/{invitation_id}` | Открыть приглашение (кандидату — автоматически статус viewed) | 🔒 |
| `POST` | `/api/invitations/{invitation_id}/accept` | Кандидат: принять — контакты станут видны работодателю | 🔒 |
| `POST` | `/api/invitations/{invitation_id}/decline` | Кандидат: отклонить | 🔒 |
| `PATCH` | `/api/invitations/{invitation_id}/answer` | Кандидат: ответить одним запросом (status = accepted | rejected) | 🔒 |
| `POST` | `/api/invitations/{invitation_id}/withdraw` | Работодатель: отозвать приглашение | 🔒 |
| `PUT` | `/api/invitations/{invitation_id}/contact-access` | Кандидат: закрыть свои контакты от компании (или открыть снова) после принятия | 🔒 |

### Вакансии и отклики

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/vacancies` | Лента вакансий (для кандидата и всех) | 🔒 |
| `POST` | `/api/vacancies` | Работодатель: опубликовать вакансию (= описать потребность) | 🔒 |
| `GET` | `/api/vacancies/mine` | Работодатель: мои вакансии | 🔒 |
| `GET` | `/api/vacancies/{vacancy_id}` | Вакансия | 🔒 |
| `PATCH` | `/api/vacancies/{vacancy_id}` | Работодатель: редактировать / закрыть (status=closed) | 🔒 |
| `GET` | `/api/vacancies/{vacancy_id}/matches` | Работодатель: подборка кандидатов под вакансию с обоснованием | 🔒 |
| `GET` | `/api/vacancies/{vacancy_id}/assessment-preview` | Как система сформирует тест под эту вакансию (2 разных варианта) | 🔒 |
| `POST` | `/api/vacancies/{vacancy_id}/apply` | Кандидат: откликнуться самому | 🔒 |
| `GET` | `/api/applications` | Отклики: кандидат — мои, работодатель — на мои вакансии (?vacancy_id=) | 🔒 |
| `PATCH` | `/api/applications/{application_id}` | Работодатель: просмотрено / принять / отклонить отклик | 🔒 |
| `POST` | `/api/applications/{application_id}/withdraw` | Кандидат: отозвать отклик | 🔒 |

### Короткие задания

| Метод | Путь | Что делает | |
|---|---|---|---|
| `POST` | `/api/short-tasks` | Работодатель: создать задание | 🔒 |
| `GET` | `/api/short-tasks/mine` | Работодатель: мои задания | 🔒 |
| `POST` | `/api/short-tasks/{task_id}/close` | Работодатель: закрыть | 🔒 |
| `GET` | `/api/short-tasks/feed` | Кандидат: задания для моей категории | 🔒 |
| `POST` | `/api/short-tasks/{task_id}/submit` | Кандидат: отправить решение или подход | 🔒 |
| `GET` | `/api/short-tasks/{task_id}/submissions` | Работодатель: решения по заданию | 🔒 |
| `POST` | `/api/short-tasks/submissions/{submission_id}/review` | Работодатель: оценить решение (0..10) | 🔒 |

### ФСП (реестр достижений)

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/fsp/registry/{fsp_id}` | Что знает реестр ФСП об участнике: реальные результаты из таблицы или демо-данные |  |

### FSP ID (имитация Keycloak)

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/mock-fsp-id/realms/fsp/.well-known/openid-configuration` | Discovery: адреса провайдера (как у Keycloak) |  |
| `GET` | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/certs` | Ключи провайдера (в имитации id_token подписан HS256 секретом клиента) |  |
| `GET` | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/auth` | Страница входа FSP ID (имитация) |  |
| `POST` | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/token` | Обмен кода на токены (имитация) |  |
| `GET` | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/userinfo` | Профиль участника FSP ID (имитация) |  |

### Служебное

| Метод | Путь | Что делает | |
|---|---|---|---|
| `GET` | `/api/health` | Проверка, что сервис жив |  |
