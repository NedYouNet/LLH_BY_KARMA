# Маршруты API

Сформировано из app.openapi(); тела запросов и ответов — в openapi.json и Swagger.

## Авторизация

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| POST | `/api/auth/register` | Регистрация кандидата или работодателя | Нет |
| POST | `/api/auth/verify-email` | Подтвердить email (токен из письма) | Нет |
| POST | `/api/auth/resend-verification` | Отправить письмо подтверждения ещё раз | Нет |
| POST | `/api/auth/login` | Вход (JSON) — для фронтенда | Нет |
| POST | `/api/auth/token` | Вход через форму — для кнопки Authorize в Swagger (username = email) | Нет |
| POST | `/api/auth/refresh` | Обновить пару токенов (ротация) | Нет |
| POST | `/api/auth/logout` | Выход (отзыв сессии) | Да |
| GET | `/api/auth/me` | Кто я + чек-лист онбординга | Да |
| GET | `/api/auth/fsp-id/config` | Показывать ли кнопку «Войти через FSP ID» | Нет |
| GET | `/api/auth/fsp-id/login` | Начать вход через FSP ID (переадресация на страницу FSP ID) | Нет |
| GET | `/api/auth/fsp-id/callback` | Сюда FSP ID возвращает пользователя после входа | Нет |

## Справочники

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/reference` | Все справочники одним запросом (кэшируйте на фронте) | Нет |

## Кандидат: профиль

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/candidate/profile` | Мой профиль | Да |
| PATCH | `/api/candidate/profile` | Обновить профиль (только присланные поля) | Да |
| POST | `/api/candidate/resume/parse` | Загрузить PDF-резюме и распознать поля | Да |
| GET | `/api/candidate/profile/pdf` | Скачать стандартизированный PDF-профиль | Да |
| POST | `/api/candidate/survey` | Шаг 1: анкета — IT-направление и грейд, на который претендую | Да |
| GET | `/api/candidate/category` | Моя категория, грейд, когда можно менять, на какие грейды можно пройти тест | Да |
| PUT | `/api/candidate/consents` | Согласия (152-ФЗ) | Да |
| PUT | `/api/candidate/privacy` | Что видно работодателю | Да |
| POST | `/api/candidate/fsp` | Привязать ФСП ID и подтянуть достижения из реестра | Да |
| DELETE | `/api/candidate/fsp` | Отвязать ФСП ID | Да |
| GET | `/api/candidate/contact-access-log` | Кто и когда получил доступ к моим контактам | Да |
| GET | `/api/candidate/export` | Выгрузить все мои данные (JSON) | Да |
| DELETE | `/api/candidate/account` | Удалить аккаунт и все мои данные | Да |

## Кандидат: тестирование

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/testing/attempts` | История моих попыток | Да |
| POST | `/api/testing/attempts` | Шаг 2–3: выбрать грейд и начать тест | Да |
| GET | `/api/testing/attempts/{attempt_id}` | Получить попытку (например, после перезагрузки страницы) | Да |
| POST | `/api/testing/attempts/{attempt_id}/check` | Проверить код на тестах — до 10 раз на задание, без завершения попытки | Да |
| POST | `/api/testing/attempts/{attempt_id}/submit` | Отправить ответы и получить результат + решение по грейду | Да |
| GET | `/api/testing/attempts/{attempt_id}/result` | Результат завершённой попытки | Да |

## Работодатель: подбор

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/employer/profile` | Профиль компании | Да |
| PATCH | `/api/employer/profile` | Обновить профиль компании | Да |
| GET | `/api/employer/needs` | Мои сохранённые потребности («кого ищем») | Да |
| POST | `/api/employer/needs` | Сохранить новую потребность | Да |
| GET | `/api/employer/needs/{need_id}` | Одна потребность | Да |
| PUT | `/api/employer/needs/{need_id}` | Изменить потребность (присылается целиком) | Да |
| DELETE | `/api/employer/needs/{need_id}` | Удалить потребность | Да |
| GET | `/api/candidates` | Подборка через параметры адреса (удобно для фильтров на фронте) | Да |
| GET | `/api/candidates/categories` | Обзор банка: категории и сколько в них кандидатов | Да |
| POST | `/api/candidates/search` | Подборка: фильтры + ранжирование + обоснование каждого кандидата | Да |
| GET | `/api/candidates/{candidate_id}` | Карточка кандидата (контакты — только после принятия инвайта/отклика) | Да |
| GET | `/api/shortlist` | Избранные кандидаты | Да |
| POST | `/api/shortlist` | Добавить в избранное | Да |
| DELETE | `/api/shortlist/{candidate_id}` | Убрать из избранного | Да |

## Работодатель: интеграция с ATS

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/employer/integrations/ats` | Настройки отправки кандидатов в вашу ATS и последние отправки | Да |
| PUT | `/api/employer/integrations/ats` | Подключить ATS: адрес вебхука (секрет выдаётся один раз) | Да |
| DELETE | `/api/employer/integrations/ats` | Отключить интеграцию с ATS | Да |
| POST | `/api/employer/integrations/ats/test` | Отправить в ATS тестовое событие | Да |

## Приглашения (главная механика)

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| POST | `/api/invitations` | Работодатель: пригласить кандидата (вилка ЗП обязательна) | Да |
| GET | `/api/invitations` | Мои приглашения: работодатель — отправленные, кандидат — входящие | Да |
| GET | `/api/invitations/{invitation_id}` | Открыть приглашение (кандидату — автоматически статус viewed) | Да |
| POST | `/api/invitations/{invitation_id}/accept` | Кандидат: принять — контакты станут видны работодателю | Да |
| POST | `/api/invitations/{invitation_id}/decline` | Кандидат: отклонить | Да |
| PATCH | `/api/invitations/{invitation_id}/answer` | Кандидат: ответить одним запросом (status = accepted \| rejected) | Да |
| POST | `/api/invitations/{invitation_id}/withdraw` | Работодатель: отозвать приглашение | Да |
| PUT | `/api/invitations/{invitation_id}/contact-access` | Кандидат: закрыть свои контакты от компании (или открыть снова) после принятия | Да |

## Вакансии и отклики

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/vacancies` | Лента вакансий (для кандидата и всех) | Да |
| POST | `/api/vacancies` | Работодатель: опубликовать вакансию (= описать потребность) | Да |
| GET | `/api/vacancies/mine` | Работодатель: мои вакансии | Да |
| GET | `/api/vacancies/{vacancy_id}` | Вакансия | Да |
| PATCH | `/api/vacancies/{vacancy_id}` | Работодатель: редактировать / закрыть (status=closed) | Да |
| GET | `/api/vacancies/{vacancy_id}/matches` | Работодатель: подборка кандидатов под вакансию с обоснованием | Да |
| GET | `/api/vacancies/{vacancy_id}/assessment-preview` | Как система сформирует тест под эту вакансию (2 разных варианта) | Да |
| POST | `/api/vacancies/{vacancy_id}/apply` | Кандидат: откликнуться самому | Да |
| GET | `/api/applications` | Отклики: кандидат — мои, работодатель — на мои вакансии (?vacancy_id=) | Да |
| PATCH | `/api/applications/{application_id}` | Работодатель: просмотрено / принять / отклонить отклик | Да |
| POST | `/api/applications/{application_id}/withdraw` | Кандидат: отозвать отклик | Да |

## Короткие задания

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| POST | `/api/short-tasks` | Работодатель: создать задание | Да |
| GET | `/api/short-tasks/mine` | Работодатель: мои задания | Да |
| POST | `/api/short-tasks/{task_id}/close` | Работодатель: закрыть | Да |
| GET | `/api/short-tasks/feed` | Кандидат: задания для моей категории | Да |
| POST | `/api/short-tasks/{task_id}/submit` | Кандидат: отправить решение или подход | Да |
| GET | `/api/short-tasks/{task_id}/submissions` | Работодатель: решения по заданию | Да |
| POST | `/api/short-tasks/submissions/{submission_id}/review` | Работодатель: оценить решение (0..10) | Да |

## ФСП (реестр достижений)

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/fsp/registry/{fsp_id}` | Что знает реестр ФСП об участнике: реальные результаты из таблицы или демо-данные | Нет |

## FSP ID (имитация Keycloak)

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/mock-fsp-id/realms/fsp/.well-known/openid-configuration` | Discovery: адреса провайдера (как у Keycloak) | Нет |
| GET | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/certs` | Ключи провайдера (в имитации id_token подписан HS256 секретом клиента) | Нет |
| GET | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/auth` | Страница входа FSP ID (имитация) | Нет |
| POST | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/token` | Обмен кода на токены (имитация) | Нет |
| GET | `/api/mock-fsp-id/realms/fsp/protocol/openid-connect/userinfo` | Профиль участника FSP ID (имитация) | Нет |

## Тестовый приёмник ATS (имитация)

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| POST | `/api/mock-ats/webhook` | Принять событие платформы, как это сделала бы ATS (проверка подписи) | Нет |
| GET | `/api/mock-ats/events` | Работодатель: что получил тестовый приёмник (последние 20 событий) | Да |

## Служебное

| Метод | Путь | Назначение | Токен |
|---|---|---|---|
| GET | `/api/health` | Проверка, что сервис жив и какой код запущен | Нет |
