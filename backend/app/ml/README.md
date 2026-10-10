# Интеграция ML в бэкенд — инструкция для участника 3 (ML)

Привет! Интеграцию ML с бэкендом делаешь ты, бэкендер её не трогает. Ниже всё, что нужно, чтобы встроить
твой код (разбор резюме на GigaChat, похожесть, объяснимый матчинг, задания и грейдер) без поломок.
Порядок такой: **сначала прочитай раздел 0 и 1, потом выбери вариант A или B в разделе 2**.

Если где-то нужно изменить что-то **вне** папок, перечисленных в разделе 1, — сначала напиши бэкендеру.

---

## 0. Как устроен проект и как его запустить

```
LLH_BY_KARMA/
  backend/                основной бэкенд: FastAPI 0.115 + PostgreSQL 16, Python 3.12 (в Docker)
    app/
      ml/                 ← ТВОЯ ПАПКА: resume.py, matching.py (+ любые свои модули)
      testing_bank/       ← банк заданий (bank.py) — твоя зона
      services/           бизнес-логика (ml_client.py — как бэкенд вызывает ML)
      api/routers/        HTTP-эндпоинты
      models/ schemas/    таблицы БД и схемы API (не менять без бэкендера)
      reference.py        справочник: коды направлений, грейдов, навыков
    tests/                автотесты (pytest), в т.ч. test_ml_contract.py — контракт с тобой
    scripts/              seed (демо-данные), evaluate (валидация подбора), load_test (нагрузка)
    requirements.txt      библиотеки бэкенда с точными версиями
  ml/                     ← (только для варианта B) твой отдельный сервис
  docs/                   документация для жюри (твоя — docs/11_ml.md)
  docker-compose.yml      запуск всего одной командой
```

**Запуск** (нужен Docker Desktop):

```bash
docker compose up --build                                   # из корня репозитория, первая вкладка терминала
docker compose exec backend python -m scripts.seed --reset  # вторая вкладка: демо-данные
```

- Swagger бэкенда: http://localhost:8000/docs · проверка версии: http://localhost:8000/api/health
- Демо-кандидат: `candidate@demo.ru` / `demo12345`, работодатель: `employer@demo.ru` / `demo12345`
- Порт **8000 занят основным бэкендом**. Если запускаешь свой сервис отдельно — используй **8001**.

Как авторизоваться в Swagger: `POST /api/auth/login` → скопировать `access_token` → кнопка **Authorize** вверху.

---

## 1. Правила (важно, требования организаторов и 152-ФЗ)

1. **Ключ GigaChat — только в переменной окружения `GIGA_TOKEN`**, читать через `os.environ.get("GIGA_TOKEN")`.
   Не в `config.py`, не в коде, не в git: репозиторий будет публичным. Локально ключ кладётся в файл `.env`
   в корне (рядом с `docker-compose.yml`), этот файл уже в `.gitignore`.
2. **Демо обязано работать без ключа.** У жюри может не быть токена GigaChat. Без ключа или при ошибке
   функция возвращает `None` (или бросает исключение) — бэкенд сам переключается на встроенный парсер.
   Это уже сделано на стороне бэкенда, тебе нужно только не «ронять» процесс (никаких `sys.exit`).
3. **Персональные данные в LLM — минимум.** Перед отправкой текста резюме в GigaChat вырезай почту,
   телефон и Telegram. Готовая функция: `from app.services.ml_client import _mask_contacts`. Контакты бэкенд
   находит сам, их возвращать не обязательно.
4. **Без видеокарты.** Стенд жюри — обычный CPU.
5. **Время ответа:** разбор резюме — до 20 секунд (`ML_TIMEOUT_SECONDS`), похожесть — миллисекунды на кандидата.
6. **Новые библиотеки** — в `backend/requirements.txt` (вариант A) или `ml/requirements.txt` (вариант B),
   строго с версией: `gigachat==X.Y.Z`. Проверь, что версия реально ставится (раздел 6, шаг 1).
7. **Фронтенд не ходит в ML напрямую.** Все запросы идут через основной бэкенд: там авторизация, роли и
   защита ПДн. Поэтому `CORS *` в твоём сервисе не нужен, а для варианта B порт 8001 — только для отладки.
8. **Цифры в документации — только реально измеренные.** Если в README стоят примерные проценты
   («95% / 90% / 100%, заполните своими данными») — их либо измерить и описать как, либо убрать.
   Жюри может попросить воспроизвести.
9. Можно менять: `backend/app/ml/**`, `backend/app/testing_bank/**`, `backend/requirements.txt` (добавить
   строки), `ml/**`, `docs/11_ml.md`, свой раздел в `docs/07_libraries.md`, блок `ml` в `docker-compose.yml`
   и строку `GIGA_TOKEN` у `backend`. Всё остальное — через бэкендера.

---

## 2. Разбор резюме: выбери вариант A или B

Бэкенд при загрузке PDF (`POST /api/candidate/resume/parse`) пробует по очереди:
**A** (функция внутри бэкенда) → **B** (твой сервис по адресу `ML_SERVICE_URL`) → встроенный парсер.
Достаточно сделать **один** вариант.

| | Вариант A: код внутри бэкенда | Вариант B: отдельный сервис |
|---|---|---|
| Где код | `backend/app/ml/resume.py` | папка `ml/` в корне, свой FastAPI |
| Контейнеров | один (бэкенд) | два (бэкенд + ml) |
| Что настроить | `ENABLED = True`, `GIGA_TOKEN` в compose | раскомментировать блок `ml`, `ML_SERVICE_URL`, `GIGA_TOKEN` |
| Плюсы | проще запуск у жюри, нет сети между сервисами | твой код остаётся как есть, свой Swagger |
| Рекомендация | **проще и надёжнее для демо** | если сервис уже готов и не хочется переносить |

### Вариант A — код внутри бэкенда (рекомендуем)

**Шаг A1.** Добавь библиотеку в `backend/requirements.txt` (с точной версией), например:
```
gigachat==X.Y.Z   # GigaChat API: разбор резюме (участник 3)
```

**Шаг A2.** Передай ключ в контейнер бэкенда. В `docker-compose.yml`, сервис `backend`, блок `environment`,
добавь строку:
```yaml
      GIGA_TOKEN: ${GIGA_TOKEN:-}
```
А в файл `.env` в корне репозитория (создай, если нет; **не коммитить**):
```
GIGA_TOKEN=твой_ключ_авторизации
```

**Шаг A3.** Реализуй `backend/app/ml/resume.py`. Контракт (бэкенд вызывает именно так):

```python
ENABLED = True

def parse_resume(pdf_bytes: bytes, text: str, filename: str) -> dict | None:
    ...
```
- `pdf_bytes` — исходный PDF (до 5 МБ, уже проверено, что это PDF);
- `text` — текст, уже извлечённый бэкендом из PDF (pypdf). Обычно достаточно его;
- `filename` — имя файла.

Вернуть словарь с **любыми** из полей (лишние ключи игнорируются, отсутствующие — не страшно):

| Поле | Тип | Значения |
|---|---|---|
| `full_name` | str | «Иван Петров». Если не нашёл — не возвращай (не пиши «Не указано») |
| `skills` | list[str] | навыки; лучше писать как в справочнике `app/reference.py` (`SKILLS`), например `"Python"`, `"FastAPI"` |
| `soft_skills`, `team_roles` | list[str] | из `SOFT_SKILLS`, `TEAM_ROLES` в `app/reference.py` |
| `experience_years` | float | 0–60 |
| `specialization_guess` | str | строго один из кодов: `backend`, `frontend`, `data_science`, `qa`, `devops` |
| `grade_guess` | str | строго один из кодов: `intern`, `junior`, `middle`, `senior` (маленькими буквами!) |
| `city`, `about` | str | город, краткое «о себе» |
| `email`, `phone`, `telegram` | str | можно не заполнять: бэкенд найдёт их сам |

Вернуть `None` = «не смог» → бэкенд возьмёт встроенный парсер. Исключения тоже перехватываются.

Готовый каркас, который можно взять за основу:

```python
"""Разбор резюме через GigaChat (участник 3)."""
import json
import logging
import os

from app.reference import ALL_SKILLS, GRADE_CODES, SPEC_CODES
from app.services.ml_client import _mask_contacts

log = logging.getLogger("ml")
ENABLED = True

PROMPT = (
    "Извлеки из резюме данные и верни ТОЛЬКО JSON без пояснений: "
    '{"full_name": str|null, "skills": [str], "experience_years": number|null, '
    '"specialization_guess": один из ' + str(SPEC_CODES) + ', '
    '"grade_guess": один из ' + str(GRADE_CODES) + "}.\n\nРезюме:\n"
)


def parse_resume(pdf_bytes: bytes, text: str, filename: str) -> dict | None:
    token = os.environ.get("GIGA_TOKEN")
    if not token or not text.strip():
        return None                                   # нет ключа — бэкенд возьмёт встроенный парсер
    from gigachat import GigaChat                     # импорт внутри: без библиотеки бэкенд всё равно стартует
    with GigaChat(credentials=token, verify_ssl_certs=False, timeout=15) as giga:
        answer = giga.chat(PROMPT + _mask_contacts(text)[:12000]).choices[0].message.content
    data = json.loads(answer[answer.find("{"): answer.rfind("}") + 1])   # LLM иногда добавляет текст вокруг JSON
    canon = {s.lower(): s for s in ALL_SKILLS}
    out = {
        "full_name": data.get("full_name") or None,
        "skills": [canon.get(str(s).lower(), str(s)) for s in data.get("skills") or []],
        "experience_years": data.get("experience_years"),
    }
    if str(data.get("grade_guess", "")).lower() in GRADE_CODES:
        out["grade_guess"] = str(data["grade_guess"]).lower()
    if data.get("specialization_guess") in SPEC_CODES:
        out["specialization_guess"] = data["specialization_guess"]
    return out
```
Параметры `GigaChat(...)` (`scope`, `model`, проверка сертификатов) сверь с документацией своей версии библиотеки.
Для детерминированности поставь низкую температуру.

**Шаг A4.** Проверка — раздел 6.

### Вариант B — твой отдельный сервис

**Шаг B1.** Положи код сервиса в папку `ml/` в корне репозитория: `main.py`, свои модули, `requirements.txt`,
`Dockerfile`. Базовый образ — `python:3.12-slim`, как у бэкенда. Внутри контейнера сервис слушает **8000**:
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Шаг B2.** Ключ читается так: `os.environ.get("GIGA_TOKEN")`. Удали ключ из `config.py`, если он там был.

**Шаг B3.** В `docker-compose.yml` блок `ml` уже подготовлен — просто убери `#` у этих строк:
```yaml
  ml:
    build: ./ml
    environment:
      GIGA_TOKEN: ${GIGA_TOKEN:-}
    ports:
      - "8001:8000"
```

**Шаг B4.** В файл `.env` в корне (не коммитить):
```
ML_SERVICE_URL=http://ml:8000
GIGA_TOKEN=твой_ключ_авторизации
```
`ml` — имя сервиса в Docker-сети, поэтому адрес именно `http://ml:8000`, а не localhost.

**Шаг B5.** Контракт, который бэкенд **уже** вызывает (`app/services/ml_client.py → parse_resume_via_ml`):

```
POST {ML_SERVICE_URL}/api/cv/parse
Content-Type: application/json
{"cv_text": "текст резюме, где почта/телефон/Telegram заменены на [email], [телефон], [telegram]"}

200 OK
{"full_name": "Иван Петров", "grade": "Middle", "skills": ["Python", "FastAPI"], "experience_years": 3}
```
Как бэкенд читает ответ:
- `grade` — любой регистр («Middle» → `middle`); неизвестное значение игнорируется;
- `skills` — приводятся к написанию из справочника; по ним бэкенд сам определяет направление (`backend` и т.д.);
- `full_name` = «Не указано» / пусто — игнорируется;
- любой код ответа, кроме 200 (500 без токена, 502 «мусор» от LLM), и таймаут 20 с → встроенный парсер.

Если хочешь отдавать больше полей (`specialization_guess`, `soft_skills`, `city`) — допиши их маппинг в
функции `_from_ml_service` в `backend/app/services/ml_client.py` и добавь проверку в
`tests/test_ml_contract.py::test_ml_service_contract_cv_parse`.

**Шаг B6.** Проверка — раздел 6.

---

## 3. Похожесть «вакансия ↔ кандидат» (по желанию)

Файл `backend/app/ml/matching.py`:
```python
ENABLED = True

def text_similarity(query: str, candidate_text: str) -> float:   # от 0 до 1
    ...
```
- `query` — описание вакансии/потребности + требуемый стек; `candidate_text` — «о себе» + навыки + резюме.
- Результат заменяет встроенный TF-IDF в компоненте `text` формулы ранжирования (вес 0.05). Остальная
  формула (тест, стек, ФСП, активность) и плашки «почему он» не меняются.
- **Вызывается для каждого кандидата** в выдаче — до сотен раз за один запрос работодателя. Поэтому
  **вызывать GigaChat здесь нельзя**: подборка будет грузиться минутами. Подходит только локальное и быстрое:
  TF-IDF/BM25, эмбеддинги небольшой модели на CPU с кешем, словари синонимов.
- Ошибка внутри функции не страшна: компонента `text` просто выпадает из расчёта.
- Проверка, стало ли лучше: `python -m scripts.evaluate` → сравнить `precision_at_10` и `ndcg_at_10`
  до и после (сейчас P@10 = 0.278). Если стало хуже — оставь `ENABLED = False`.

## 4. Объяснимый матчинг через LLM (`/api/match`) — только по согласованию

Объяснение «почему он» уже есть: каждая карточка выдачи содержит `reasons` и `breakdown`
(`app/services/matching_engine.py`). Если хочешь добавить LLM-объяснение с «за/против»:
- это **новый эндпоинт**, его вызывает фронтенд — договорись с бэкендером и фронтендером;
- вызывать **только по кнопке на карточке одного кандидата** (`GET /api/employer/candidates/{id}` открыт →
  кнопка «Объяснение ИИ»), никогда для всей выдачи;
- в LLM отправлять обезличенный профиль: навыки, грейд, опыт, «о себе» без контактов, без ФИО;
- без ключа — понятная ошибка 503, а не падение.

## 5. Задания и проверка кода (твоя зона)

Тест платформы (`/api/testing/*`) берёт задания из `backend/app/testing_bank/bank.py`, движок
`app/services/testing_engine.py` собирает тест по плану 5/3/2 и ставит грейд. Код кандидата уже проверяется
на сервере: `app/services/code_runner.py` — AST-проверка опасных конструкций + отдельный процесс с лимитами
времени и памяти. Свой sandbox на `subprocess` писать не нужно — используй этот.

**Формат шаблона** (так твои задания попадут в платформенный тест):
```python
@_add("be.code.мой_id", "backend", 1, "Алгоритмы", "code")   # id, направление, уровень 0..3, навык, вид
def _(rng):                                                   # rng — генератор случайных чисел варианта
    k = rng.randint(5, 15)                                    # параметры меняются от варианта к варианту
    tests = [{"args": [[1, 2, 3], k], "expected": ...}, ...]  # скрытые тесты = твои invariants
    return {"text": "Условие (можно с легендой)...",
            "answer": None,
            "code": {"function_name": "solve", "signature": "def solve(nums: list[int], k: int) -> int:",
                     "examples": [{"args": [...], "expected": ...}],   # видимые примеры = твои public_tests
                     "tests": tests}}
```
- Виды: `single` (выбор: `options` + `answer`), `input` (короткий ответ: `answer`), `code` (как выше).
- Уровни: `0` Intern, `1` Junior, `2` Middle, `3` Senior. Направления — коды из `app/reference.py`.
- Твой `public_tests: {"input": [...], "expected": ...}` = наш `examples: {"args": [...], "expected": ...}`.
- Главное требование организаторов: одинаковые задания не должны расходиться между кандидатами — числа и
  данные должны меняться от варианта к варианту (через `rng`).
- **Легенды от GigaChat:** не вызывай LLM во время теста (медленно, у жюри может не быть ключа). Сгенерируй
  легенды заранее, сохрани в файл рядом с `bank.py` и выбирай через `rng.choice(...)`.
- Правильные ответы и скрытые тесты **никогда** не уходят на фронтенд — это уже обеспечено движком.
- После изменений банка: `pytest -q` и `python -m scripts.evaluate` (часть A — точность грейда).

---

## 6. Проверка (обязательно перед отправкой кода)

**Шаг 1. Библиотеки ставятся.**
```bash
docker compose build backend      # вариант A
docker compose build ml           # вариант B
```
Ошибка `No matching distribution found` — такой версии нет, поправь версию в requirements.

**Шаг 2. Автотесты** (должны быть все зелёные; сейчас их 79). Папка `tests/` в образ не входит, поэтому
запускаем отдельный временный контейнер, в который подключена папка `backend` с твоими изменениями
(из корня репозитория, одной строкой; работает и в PowerShell, и в bash; Python ставить не нужно):
```bash
docker compose run --rm --no-deps -e ML_SERVICE_URL= -v "${PWD}/backend:/app" backend sh -c "pip install --user -q pytest==8.3.5 && python -m pytest -q -p no:cacheprovider"
```
Только контракт с ML — то же самое, но в конце `python -m pytest -q -p no:cacheprovider tests/test_ml_contract.py`.
Тесты работают на своей временной базе в памяти — демо-данные не трогают, GigaChat не вызывают.
Если Python 3.12 стоит у тебя локально, можно проще: `cd backend && pip install -r requirements-dev.txt && pytest -q`.

**Шаг 3. Живая проверка в Swagger** (http://localhost:8000/docs):
1. `POST /api/auth/login` под `newbie@demo.ru` / `demo12345` → Authorize с `access_token`.
2. `POST /api/candidate/resume/parse` → загрузить PDF-резюме, `apply = false`.
3. В ответе должно быть `"source": "ml"` (сработала твоя модель) и заполненные `fields`.
   `"source": "fallback"` — твоя часть не сработала: смотри логи (шаг 4).

**Шаг 4. Логи**, если что-то не так:
```bash
docker compose logs backend --tail 100     # строки "ML-разбор резюме упал..." / "ML-сервис недоступен..."
docker compose logs ml --tail 100          # вариант B
```

**Шаг 5. Без ключа демо работает.** Убери `GIGA_TOKEN` из `.env`, `docker compose up -d`, повтори шаг 3 —
должно быть `"source": "fallback"` и **без ошибок**.

**Шаг 6. Валидация подбора** (если трогал `matching.py`):
```bash
docker compose exec backend python -m scripts.evaluate
```

## 7. Документация (обязательное требование организаторов)

1. Создай `docs/11_ml.md`:
   - какие модели используются (GigaChat-2-Pro / Max и т.д.), **как и зачем** каждая;
   - почему российская модель (152-ФЗ) и какие данные уходят в LLM (резюме без контактов);
   - что происходит без ключа (встроенный парсер);
   - откуда задания банка и как устроена защита от списывания;
   - как проверяли качество: методика, сколько примеров, **реально полученные** цифры, как воспроизвести.
2. Добавь свои библиотеки с версиями в `docs/07_libraries.md`, раздел «ML-часть».
3. Добавь строку про свой раздел в таблицу документации в `README.md` в корне (пункт `+`).
4. Разделы про FSP ID, общий API и сборку не дублируй — они уже есть в `docs/05`, `docs/06`, `docs/08`.

## 8. Как отдать работу

- Работай в отдельной ветке `ml` (от актуальной `main` или `backend`), коммить только свои файлы.
- **Никогда не коммить `.env` и ключи.** Перед коммитом: `git status` — файла `.env` в списке быть не должно.
- Перед отправкой: раздел 6, шаги 1–5. Затем напиши бэкендеру, что ветка готова, и какой вариант (A или B)
  выбран — для итоговой проверки и объединения в `main`.

## Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `"source": "fallback"`, в логах `ML-сервис недоступен ... Name or service not known` | В `ML_SERVICE_URL` написано `localhost`. Нужно `http://ml:8000` |
| `port is already allocated` на 8000 | Твой сервис пытается занять порт бэкенда. Снаружи — `8001:8000` |
| В ответе `grade_guess` пустой | Возвращаешь «Middle» с большой буквы или по-русски. Нужны коды `intern/junior/middle/senior` (в варианте B регистр бэкенд исправит сам) |
| Разбор резюме висит 20 с и уходит в fallback | GigaChat отвечает дольше `ML_TIMEOUT_SECONDS`. Сократи текст/промпт или поставь таймаут клиента ~15 с |
| `json.decoder.JSONDecodeError` | LLM добавила текст вокруг JSON. Вырезай от первой `{` до последней `}` (см. каркас) |
| Бэкенд не стартует после добавления библиотеки | Конфликт версий с `pydantic`/`httpx` бэкенда. Посмотри `docker compose logs backend`, подбери совместимую версию |
| Подборка работодателя стала грузиться секундами | В `text_similarity` есть сетевой вызов. Там только локальные вычисления (раздел 3) |
