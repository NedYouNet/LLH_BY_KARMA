"""
Шаблоны заданий по специализациям.

Каждый шаблон умеет `make(rng)` -> словарь:
    text     — текст задания
    options  — варианты ответа (для kind="single")
    answer   — правильный ответ (НИКОГДА не уходит на фронтенд)
    code     — для kind="code": имя функции, видимые примеры и скрытые тесты

Виды заданий:
    single — выбор одного варианта
    input  — ввести короткий ответ (число/строку)
    code   — написать функцию на Python (проверяется на сервере скрытыми тестами)

Как добавить своё задание: скопируй любую функцию-генератор ниже, поменяй текст,
и зарегистрируй через `_add(...)`.
"""
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    id: str
    spec: str
    level: int
    skill: str
    kind: str  # single | input | code
    make: Callable[[random.Random], dict]
    parametric: bool = True  # False = фиксированный текст (уникализируется только перемешиванием)


TEMPLATES: list[Template] = []


def _add(id_: str, spec: str, level: int, skill: str, kind: str):
    """Декоратор: регистрирует функцию-генератор как шаблон задания."""
    def wrap(fn: Callable[[random.Random], dict]):
        TEMPLATES.append(Template(id_, spec, level, skill, kind, fn))
        return fn
    return wrap


def _static(id_: str, spec: str, level: int, skill: str, text: str, correct: str, wrong: list[str]) -> None:
    """Вопрос с фиксированным текстом: уникализируется перемешиванием вариантов."""
    def make(rng: random.Random) -> dict:
        options = [correct, *wrong]
        rng.shuffle(options)
        return {"text": text, "options": options, "answer": correct}
    TEMPLATES.append(Template(id_, spec, level, skill, "single", make, parametric=False))


def _choice(rng: random.Random, correct, wrong: list) -> tuple[list[str], str]:
    """Собирает перемешанные варианты (все приводим к строке, убираем дубли)."""
    opts = [str(correct)]
    for w in wrong:
        if str(w) not in opts:
            opts.append(str(w))
    rng.shuffle(opts)
    return opts, str(correct)


def templates_for(spec: str) -> list[Template]:
    return [t for t in TEMPLATES if t.spec == spec]


# =====================================================================
#                              BACKEND
# =====================================================================

@_add("be.py.comprehension", "backend", 0, "Python", "input")
def _(rng):
    a, b = rng.randint(15, 60), rng.randint(2, 7)
    ans = len([x for x in range(a) if x % b == 0])
    return {"text": f"Что выведет код?\n\nprint(len([x for x in range({a}) if x % {b} == 0]))", "answer": str(ans)}


@_add("be.py.slice", "backend", 0, "Python", "input")
def _(rng):
    word = rng.choice(["hackathon", "federation", "programming", "algorithm", "database", "backend"])
    i = rng.randint(0, 3)
    j = rng.randint(i + 2, len(word))
    return {"text": f"Что выведет код?\n\ns = \"{word}\"\nprint(s[{i}:{j}])", "answer": word[i:j]}


@_add("be.http.codes", "backend", 0, "REST", "single")
def _(rng):
    cases = [("ресурс успешно создан (POST)", "201", ["200", "204", "302"]),
             ("нет токена или он невалиден", "401", ["403", "400", "404"]),
             ("токен валиден, но прав недостаточно", "403", ["401", "404", "409"]),
             ("запрос конфликтует с текущим состоянием ресурса", "409", ["400", "422", "500"]),
             ("успешно, но тело ответа пустое", "204", ["200", "201", "304"])]
    situation, correct, wrong = rng.choice(cases)
    opts, ans = _choice(rng, correct, wrong)
    return {"text": f"Какой HTTP-код правильно вернуть, если {situation}?", "options": opts, "answer": ans}


@_add("be.sql.where", "backend", 0, "SQL", "input")
def _(rng):
    values = [rng.randint(1, 100) for _ in range(rng.randint(6, 9))]
    k = rng.randint(20, 80)
    rows = ", ".join(f"({v})" for v in values)
    return {"text": f"Таблица t(x) содержит строки: {rows}.\nСколько строк вернёт запрос?\n\n"
                    f"SELECT COUNT(*) FROM t WHERE x > {k};", "answer": str(sum(v > k for v in values))}


@_add("be.py.dict", "backend", 1, "Python", "input")
def _(rng):
    keys = rng.sample(["a", "b", "c", "d", "e"], 3)
    d1 = {k: rng.randint(1, 9) for k in keys}
    upd_key = rng.choice(keys)
    new_key = rng.choice([k for k in ["x", "y", "z"]])
    u = {upd_key: rng.randint(10, 20), new_key: rng.randint(1, 9)}
    d = dict(d1)
    d.update(u)
    return {"text": f"Что выведет код?\n\nd = {d1}\nd.update({u})\nprint(sum(d.values()))", "answer": str(sum(d.values()))}


@_add("be.py.mutable_default", "backend", 1, "Python", "input")
def _(rng):
    n = rng.randint(2, 5)
    calls = "\n".join(f"f({i})" for i in range(n))
    return {"text": "Что выведет код?\n\ndef f(x, acc=[]):\n    acc.append(x)\n    return acc\n\n"
                    f"{calls}\nprint(len(f(99)))", "answer": str(n + 1)}


@_add("be.sql.join", "backend", 1, "SQL", "input")
def _(rng):
    users = list(range(1, rng.randint(4, 6) + 1))
    orders = [rng.choice(users + [99]) for _ in range(rng.randint(5, 8))]
    ans = sum(1 for o in orders if o in users)
    return {"text": f"users(id): {users}\norders(user_id): {orders}\n\n"
                    "Сколько строк вернёт запрос?\nSELECT * FROM users u JOIN orders o ON o.user_id = u.id;",
            "answer": str(ans)}


_static("be.http.idempotent", "backend", 1, "REST", "Какой HTTP-метод НЕ является идемпотентным?",
        "POST", ["PUT", "DELETE", "GET"])


@_add("be.algo.complexity", "backend", 2, "Алгоритмы", "single")
def _(rng):
    cases = [("бинарный поиск в отсортированном массиве из n элементов", "O(log n)", ["O(n)", "O(n log n)", "O(1)"]),
             ("поиск ключа в dict Python (в среднем)", "O(1)", ["O(log n)", "O(n)", "O(n²)"]),
             ("сортировка списка через sorted()", "O(n log n)", ["O(n)", "O(n²)", "O(log n)"]),
             ("проверка `x in list` для списка из n элементов", "O(n)", ["O(1)", "O(log n)", "O(n log n)"]),
             ("два вложенных цикла по одному массиву из n элементов", "O(n²)", ["O(n)", "O(n log n)", "O(2ⁿ)"])]
    what, correct, wrong = rng.choice(cases)
    opts, ans = _choice(rng, correct, wrong)
    return {"text": f"Какова временная сложность: {what}?", "options": opts, "answer": ans}


_static("be.db.index", "backend", 2, "PostgreSQL",
        "Частый запрос: WHERE company_id = ? AND created_at > ? ORDER BY created_at. Какой индекс подойдёт лучше всего?",
        "Составной индекс (company_id, created_at)",
        ["Два отдельных индекса: company_id и created_at", "Индекс только по created_at", "Индекс (created_at, company_id)"])

_static("be.py.generator", "backend", 2, "Python",
        "g = (x * x for x in range(5)); a = sum(g); b = sum(g). Чему равно b?",
        "0", ["30", "60", "Будет исключение StopIteration"])


def _pairs_ref(nums: list[int], k: int) -> int:
    return sum(1 for i in range(len(nums)) for j in range(i + 1, len(nums)) if nums[i] + nums[j] == k)


@_add("be.code.pairs", "backend", 2, "Алгоритмы", "code")
def _(rng):
    k = rng.randint(5, 15)
    tests = []
    for _ in range(6):
        nums = [rng.randint(0, k) for _ in range(rng.randint(0, 12))]
        tests.append({"args": [nums], "expected": _pairs_ref(nums, k)})
    example = [1, k - 1, 2, k - 2, k - 1]
    return {"text": f"Напишите функцию solve(nums), которая возвращает количество пар индексов i < j, "
                    f"для которых nums[i] + nums[j] == {k}.\n\nПример: solve({example}) == {_pairs_ref(example, k)}",
            "answer": None,
            "code": {"function_name": "solve", "signature": "def solve(nums: list[int]) -> int:",
                     "examples": [{"args": [example], "expected": _pairs_ref(example, k)}], "tests": tests}}


_static("be.db.isolation", "backend", 3, "PostgreSQL",
        "Какую аномалию предотвращает уровень изоляции REPEATABLE READ по сравнению с READ COMMITTED?",
        "Неповторяющееся чтение (non-repeatable read)", ["Грязное чтение (dirty read)", "Потерянное обновление при любых условиях", "Взаимную блокировку (deadlock)"])

_static("be.arch.idempotency", "backend", 3, "REST",
        "Клиент повторяет POST /payments при таймауте сети. Как защититься от двойного списания?",
        "Ключ идемпотентности в заголовке + уникальный индекс в БД",
        ["Увеличить таймаут клиента", "Перейти на метод PUT без изменений логики", "Логировать все запросы"])

_static("be.arch.queue", "backend", 3, "Kafka",
        "Консьюмер Kafka упал после обработки сообщения, но до коммита offset. Что произойдёт после рестарта?",
        "Сообщение будет обработано повторно — нужна идемпотентная обработка",
        ["Сообщение потеряется", "Kafka автоматически откатит изменения в БД", "Консьюмер пропустит партицию"])


def _topk_ref(nums: list[int], k: int) -> list[int]:
    cnt = Counter(nums)
    return [x for x, _ in sorted(cnt.items(), key=lambda p: (-p[1], p[0]))[:k]]


@_add("be.code.topk", "backend", 3, "Алгоритмы", "code")
def _(rng):
    k = rng.randint(2, 4)
    tests = []
    for _ in range(6):
        nums = [rng.randint(1, 9) for _ in range(rng.randint(k, 25))]
        tests.append({"args": [nums], "expected": _topk_ref(nums, k)})
    example = [3, 1, 3, 2, 2, 3, 5]
    return {"text": f"Напишите функцию solve(nums), возвращающую {k} самых частых элемента. Сортировка: "
                    f"по убыванию частоты, при равенстве — по возрастанию значения.\n\n"
                    f"Пример: solve({example}) == {_topk_ref(example, k)}",
            "answer": None,
            "code": {"function_name": "solve", "signature": "def solve(nums: list[int]) -> list[int]:",
                     "examples": [{"args": [example], "expected": _topk_ref(example, k)}], "tests": tests}}


@_add("be.arch.little", "backend", 3, "PostgreSQL", "input")
def _(rng):
    rps, ms = rng.choice([200, 300, 400, 500, 800]), rng.choice([20, 25, 40, 50])
    return {"text": f"Сервис обрабатывает {rps} запросов в секунду, каждый держит соединение с БД {ms} мс. "
                    "Сколько соединений в пуле нужно в среднем (закон Литтла)?", "answer": str(rps * ms // 1000)}


@_add("be.arch.availability", "backend", 3, "REST", "input")
def _(rng):
    a = [rng.choice([99.9, 99.5, 99.0, 99.95]) for _ in range(3)]
    total = a[0] * a[1] * a[2] / 10000
    return {"text": f"Запрос последовательно проходит через 3 сервиса с доступностью {a[0]}%, {a[1]}% и {a[2]}%. "
                    "Какова итоговая доступность? Ответ в процентах, 2 знака после точки.", "answer": f"{total:.2f}"}


@_add("be.arch.cache", "backend", 2, "Redis", "input")
def _(rng):
    h, c, d = rng.choice([80, 90, 95]), rng.choice([1, 2, 5]), rng.choice([40, 60, 100])
    avg = h / 100 * c + (1 - h / 100) * d
    return {"text": f"Hit rate кэша {h}%, ответ из кэша {c} мс, из БД {d} мс (при промахе — только БД). "
                    "Среднее время ответа в мс (1 знак после точки)?", "answer": f"{avg:.1f}"}


@_add("be.kafka.partitions", "backend", 3, "Kafka", "input")
def _(rng):
    p, c = rng.randint(3, 8), rng.randint(4, 12)
    return {"text": f"Топик Kafka с {p} партициями читает consumer group из {c} консьюмеров. "
                    "Сколько консьюмеров будут простаивать?", "answer": str(max(0, c - p))}


# =====================================================================
#                              FRONTEND
# =====================================================================

@_add("fe.js.map_filter", "frontend", 0, "JavaScript", "input")
def _(rng):
    arr = sorted(rng.sample(range(1, 15), rng.randint(4, 7)))
    k, t = rng.randint(2, 4), rng.randint(8, 30)
    ans = len([x * k for x in arr if x * k > t])
    return {"text": f"Что вернёт выражение?\n\n{arr}.map(x => x * {k}).filter(x => x > {t}).length", "answer": str(ans)}


@_add("fe.js.coercion", "frontend", 0, "JavaScript", "single")
def _(rng):
    a, b = rng.randint(1, 9), rng.randint(1, 9)
    opts, ans = _choice(rng, f'"{a}{b}"', [str(a + b), "NaN", "TypeError"])
    return {"text": f"Что вернёт выражение в JavaScript: \"{a}\" + {b}?", "options": opts, "answer": ans}


_static("fe.html.semantic", "frontend", 0, "HTML", "Какой тег семантически подходит для основной навигации сайта?",
        "<nav>", ["<div class=\"nav\">", "<section>", "<menu-bar>"])

_static("fe.css.box", "frontend", 1, "CSS", "Что делает box-sizing: border-box?",
        "width включает padding и border", ["width включает только margin", "Убирает рамку у блока", "Делает блок flex-контейнером"])

_static("fe.react.key", "frontend", 1, "React", "Зачем в React нужен атрибут key у элементов списка?",
        "Чтобы React сопоставлял элементы между рендерами", ["Для стилизации через CSS", "Это обязательный id для DOM", "Для сортировки списка"])


@_add("fe.js.closure", "frontend", 1, "JavaScript", "input")
def _(rng):
    n = rng.randint(3, 6)
    return {"text": f"Что выведет код?\n\nfor (var i = 0; i < {n}; i++) {{ setTimeout(() => console.log(i), 0) }}\n\n"
                    "Введите число, которое будет выведено (все выводы одинаковы).", "answer": str(n)}


_static("fe.js.eventloop", "frontend", 2, "JavaScript",
        "В каком порядке выполнится: console.log('A'); setTimeout(()=>console.log('B')); Promise.resolve().then(()=>console.log('C')); console.log('D')",
        "A D C B", ["A B C D", "A C D B", "A D B C"])

_static("fe.react.memo", "frontend", 2, "React", "Когда useMemo действительно полезен?",
        "Для дорогих вычислений, зависящих от редко меняющихся значений",
        ["Всегда — он ускоряет любой компонент", "Для хранения состояния формы", "Вместо useEffect для запросов"])

_static("fe.perf.render", "frontend", 3, "React", "Список из 10 000 строк тормозит при прокрутке. Лучшее решение?",
        "Виртуализация списка (рендер только видимых строк)", ["Обернуть каждую строку в useMemo", "Перейти на классовые компоненты", "Увеличить debounce скролла"])

_static("fe.arch.ssr", "frontend", 3, "Next.js", "Главное преимущество SSR для публичной страницы вакансий?",
        "Быстрый первый показ контента и индексация поисковиками", ["Меньше нагрузки на сервер", "Не нужен JavaScript вообще", "Автоматическое кэширование API"])


# =====================================================================
#                           DATA SCIENCE / ML
# =====================================================================

@_add("ds.stats.median", "data_science", 0, "Statistics", "input")
def _(rng):
    vals = [rng.randint(1, 50) for _ in range(rng.choice([5, 7]))]
    return {"text": f"Найдите медиану набора: {vals}", "answer": str(sorted(vals)[len(vals) // 2])}


_static("ds.pandas.filter", "data_science", 0, "pandas", "Как выбрать строки DataFrame df, где age > 30?",
        "df[df['age'] > 30]", ["df.where(age > 30)", "df.filter(age > 30)", "df.select('age > 30')"])


@_add("ds.metrics.precision", "data_science", 1, "Statistics", "input")
def _(rng):
    tp, fp, fn = rng.randint(20, 80), rng.randint(5, 40), rng.randint(5, 40)
    return {"text": f"TP = {tp}, FP = {fp}, FN = {fn}. Чему равна precision? Округлите до двух знаков (например 0.75).",
            "answer": f"{tp / (tp + fp):.2f}"}


_static("ds.ml.overfit", "data_science", 1, "scikit-learn",
        "Точность на train 0.99, на validation 0.71. Что это скорее всего?",
        "Переобучение", ["Недообучение", "Утечка данных из validation в train", "Нормальная ситуация"])

_static("ds.ml.leak", "data_science", 2, "scikit-learn", "Где ошибка: scaler.fit(X); X_train, X_test = split(X)?",
        "Утечка: scaler обучен на всех данных, включая test", ["Ошибки нет", "Нужно делить до импорта данных", "StandardScaler нельзя применять к test"])

_static("ds.ml.imbalance", "data_science", 2, "scikit-learn", "Классы 99:1. Какая метрика информативнее accuracy?",
        "PR-AUC / F1 по редкому классу", ["Accuracy на train", "MSE", "R²"])


def _norm_ref(nums: list[float]) -> list[float]:
    lo, hi = min(nums), max(nums)
    return [0.0 if hi == lo else round((x - lo) / (hi - lo), 3) for x in nums]


@_add("ds.code.minmax", "data_science", 2, "Python", "code")
def _(rng):
    tests = []
    for _ in range(5):
        nums = [rng.randint(-50, 50) for _ in range(rng.randint(1, 8))]
        tests.append({"args": [nums], "expected": _norm_ref(nums)})
    tests.append({"args": [[5, 5, 5]], "expected": [0.0, 0.0, 0.0]})
    ex = [2, 4, 6]
    return {"text": "Напишите solve(nums): min-max нормализация списка в [0, 1], округление до 3 знаков. "
                    "Если все значения равны — верните нули.\n\nПример: solve([2, 4, 6]) == [0.0, 0.5, 1.0]",
            "answer": None,
            "code": {"function_name": "solve", "signature": "def solve(nums: list[float]) -> list[float]:",
                     "examples": [{"args": [ex], "expected": _norm_ref(ex)}], "tests": tests}}


_static("ds.ml.boosting", "data_science", 3, "CatBoost", "Ключевое отличие бустинга от бэггинга?",
        "Модели обучаются последовательно, исправляя ошибки предыдущих", ["Модели обучаются параллельно на бутстрап-выборках", "Бустинг не использует деревья", "Бэггинг уменьшает смещение, бустинг — только дисперсию"])

_static("ds.ml.drift", "data_science", 3, "Statistics", "Модель в проде деградирует, распределение признаков сместилось. Как это называется и что делать?",
        "Data drift: мониторинг распределений (PSI/KS) и переобучение", ["Переобучение: уменьшить глубину деревьев", "Утечка: удалить признак", "Ничего — это шум"])


# =====================================================================
#                                  QA
# =====================================================================

@_add("qa.bva", "qa", 0, "Test design", "input")
def _(rng):
    lo = rng.randint(1, 20)
    hi = lo + rng.randint(10, 80)
    return {"text": f"Поле принимает целые числа от {lo} до {hi} включительно. Какое наименьшее НЕДОПУСТИМОЕ значение "
                    "сверху нужно проверить по технике граничных значений?", "answer": str(hi + 1)}


_static("qa.severity", "qa", 0, "Test design", "Опечатка в логотипе на главной странице. Обычно это…",
        "Низкая серьёзность, высокий приоритет", ["Высокая серьёзность, низкий приоритет", "Блокер", "Не баг"])

_static("qa.pyramid", "qa", 1, "Test design", "Какая форма у «пирамиды тестирования»?",
        "Больше всего юнит-тестов, меньше всего E2E", ["Больше всего E2E", "Поровну всех видов", "Только ручные тесты наверху"])

_static("qa.api", "qa", 1, "REST", "Как проверить, что работодатель НЕ видит email кандидата до принятия инвайта?",
        "API-тест: GET профиля от работодателя и проверка, что поле email = null", ["Проверить вёрстку страницы", "Посмотреть логи сервера", "Спросить разработчика"])

_static("qa.pytest.fixture", "qa", 2, "pytest", "Fixture с scope='session' создаётся…",
        "Один раз на весь прогон тестов", ["Перед каждым тестом", "Один раз на модуль", "Только при ошибке"])

_static("qa.flaky", "qa", 2, "Playwright", "Тест иногда падает из-за того, что кнопка ещё не появилась. Правильное решение?",
        "Явное ожидание состояния элемента (auto-wait / expect)", ["sleep(5) перед кликом", "Отключить тест", "Перезапускать тест до успеха"])

_static("qa.perf", "qa", 3, "JMeter", "p95 latency = 800 мс означает…",
        "95% запросов выполнились не дольше 800 мс", ["Среднее время 800 мс", "5% запросов упали", "Максимум — 800 мс"])

_static("qa.strategy", "qa", 3, "CI/CD", "Регресс занимает 6 часов. Что даст наибольший эффект?",
        "Параллелизация + выбор тестов по изменённому коду (test impact analysis)", ["Удалить половину тестов", "Запускать раз в неделю", "Перейти на ручное тестирование"])


# =====================================================================
#                                DEVOPS
# =====================================================================

@_add("ops.cidr", "devops", 0, "Linux", "input")
def _(rng):
    n = rng.randint(24, 29)
    return {"text": f"Сколько адресов для хостов в подсети /{n} (без адреса сети и broadcast)?", "answer": str(2 ** (32 - n) - 2)}


@_add("ops.chmod", "devops", 0, "Linux", "input")
def _(rng):
    perms = [rng.choice(["rwx", "rw-", "r-x", "r--"]), rng.choice(["rwx", "r-x", "r--", "---"]), rng.choice(["r-x", "r--", "---"])]
    val = "".join(str((p[0] == "r") * 4 + (p[1] == "w") * 2 + (p[2] == "x")) for p in perms)
    return {"text": f"Какое числовое значение chmod соответствует правам {''.join(perms)}?", "answer": val}


_static("ops.docker.layers", "devops", 1, "Docker", "Почему в Dockerfile COPY requirements.txt и pip install ставят ДО COPY . ?",
        "Чтобы кэш слоя с зависимостями не сбрасывался при правке кода", ["Так быстрее копируются файлы", "Иначе pip не найдёт файл", "Это требование синтаксиса"])

_static("ops.k8s.deploy", "devops", 1, "Kubernetes", "Чем Deployment отличается от Pod?",
        "Deployment управляет репликами подов и обновлениями", ["Ничем", "Pod — это группа Deployment", "Deployment — это образ контейнера"])

_static("ops.k8s.probes", "devops", 2, "Kubernetes", "Под стартует 60 секунд, и его убивают до готовности. Что настроить?",
        "startupProbe (или initialDelay у liveness)", ["Увеличить replicas", "readinessProbe с меньшим периодом", "Убрать resources.limits"])

_static("ops.cicd", "devops", 2, "CI/CD", "Как безопасно хранить пароль БД для пайплайна?",
        "В защищённых переменных/секретах CI, не в репозитории", ["В .env в репозитории", "В Dockerfile через ENV", "В README"])

_static("ops.deploy.bluegreen", "devops", 3, "Kubernetes", "Главная особенность blue-green деплоя?",
        "Две среды и мгновенное переключение трафика с быстрым откатом", ["Постепенный перевод 1% трафика", "Деплой без тестов", "Обновление по одному поду"])

_static("ops.sre.slo", "devops", 3, "Prometheus", "SLO 99.9% за 30 дней — это примерно сколько допустимого простоя?",
        "≈ 43 минуты", ["≈ 4 часа", "≈ 7 часов", "≈ 4 минуты"])


"""Банк заданий для ML-интеграции (Вариант A)"""

# =====================================================================
# 🟢 УРОВЕНЬ 0 (INTERN): Базовый синтаксис и циклы
# =====================================================================

@_add("be.code.sum_positives", "backend", 0, "Алгоритмы", "code")
def _(rng):
    # Генерация массива, гарантированно содержащего положительные числа
    arr = [rng.randint(-10, 20) for _ in range(6)]
    arr.append(rng.randint(1, 10)) 
    
    expected = sum(x for x in arr if x > 0)
    
    tests = [
        {"args": [arr], "expected": expected},
        {"args": [[-5, -2, 0, 10, 5]], "expected": 15},
        {"args": [[-1, -2, -3]], "expected": 0}
    ]
    
    legends = [
        "Бухгалтерия прислала сырой лог транзакций. Напишите функцию, которая вернет сумму всех положительных пополнений счета.",
        "Вы анализируете телеметрию датчиков умного дома. Посчитайте суммарное значение всех метрик, которые строго больше нуля."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(arr: list[int]) -> int:",
            "examples": [{"args": [[-1, 5, 2, -10]], "expected": 7}],
            "tests": tests
        }
    }


@_add("be.code.sequence_lookup", "backend", 1, "Алгоритмы", "code")
def _(rng):
    target = rng.randint(10, 50)
    base_arr = rng.sample(range(100), 7)
    if target in base_arr:
        base_arr.remove(target)
    arr = sorted(base_arr + [target])
    
    tests = [
        {"args": [arr, target], "expected": arr.index(target)},
        {"args": [[10, 20, 30, 40], 30], "expected": 2}, 
        {"args": [[target], target], "expected": 0}   
    ]
    
    legends = [
        "Найдите индекс зараженного сектора в логах сервера. Реализуйте функцию бинарного поиска за O(log n).",
        "Определите позицию посылки на складе логистической компании. Алгоритм должен работать за O(log n)."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(nums: list[int], target: int) -> int:",
            "examples": [{"args": [[10, 20, 30, 40], 30], "expected": 2}],
            "tests": tests
        }
    }

@_add("be.code.missing_number", "backend", 1, "Алгоритмы", "code")
def _(rng):
    n = rng.randint(5, 10)
    missing = rng.randint(0, n)
    arr = [i for i in range(n + 1) if i != missing]
    rng.shuffle(arr)
    
    tests = [
        {"args": [arr], "expected": missing},
        {"args": [[0, 1, 3]], "expected": 2},
        {"args": [[1, 2]], "expected": 0}
    ]
    
    legends = [
        "В базе данных инвентаризации пропал один серийный номер товара (от 0 до N). Найдите недостающий номер за O(n).",
        "Сетевой протокол потерял один пакет данных в последовательности от 0 до N. Вычислите номер потерянного пакета."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(arr: list[int]) -> int:",
            "examples": [{"args": [[3, 0, 1]], "expected": 2}],
            "tests": tests
        }
    }


@_add("be.code.continuous_stream", "backend", 2, "Алгоритмы", "code")
def _(rng):
    k = rng.randint(2, 4)
    arr = [rng.randint(1, 20) for _ in range(8)]
    
    max_sum = 0
    for i in range(len(arr) - k + 1):
        max_sum = max(max_sum, sum(arr[i:i+k]))
        
    tests = [
        {"args": [arr, k], "expected": max_sum},
        {"args": [[5, 1, 9, 2], 2], "expected": 10} 
    ]
    
    legends = [
        f"Анализ пиковой нагрузки DDoS-атаки. Найдите максимальную сумму подмассива фиксированного размера K={k} за O(n).",
        f"Анализ непрерывного потока биржевых метрик. Найдите отрезок длины {k} с максимальной доходностью (сложность O(n))."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(arr: list[int], k: int) -> int:",
            "examples": [{"args": [[1, 4, 2, 10, 2], 3], "expected": 16}],
            "tests": tests
        }
    }

@_add("be.code.first_unique", "backend", 2, "Структуры данных", "code")
def _(rng):
    # Генерация массива с одним гарантированно уникальным элементом
    repeats = [rng.randint(1, 10) for _ in range(3)]
    unique_elem = rng.randint(11, 20)
    arr = repeats + repeats + [unique_elem]
    rng.shuffle(arr)
    
    # Находим первый уникальный
    expected = -1
    for x in arr:
        if arr.count(x) == 1:
            expected = x
            break
            
    tests = [
        {"args": [arr], "expected": expected},
        {"args": [[4, 2, 4, 3, 2]], "expected": 3},
        {"args": [[1, 1, 2, 2]], "expected": -1}
    ]
    
    legends = [
        "В потоке логов пользователей нужно найти первый ID сессии, который встретился ровно один раз. Решите за O(n) с использованием хэш-таблицы.",
        "Анализ игровой статистики: найдите ID первого уникального артефакта в инвентаре игрока, который не имеет дубликатов."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(arr: list[int]) -> int:",
            "examples": [{"args": [[4, 5, 4]], "expected": 5}],
            "tests": tests
        }
    } 

@_add("be.code.network_routing", "backend", 3, "Алгоритмы", "code")
def _(rng):
    edges = [[0, 2], [2, 4], [0, 1], [1, 3], [3, 4], [1, 5]]
    rng.shuffle(edges)
    
    tests = [
        {"args": [6, edges, 0, 4], "expected": 2}, 
        {"args": [5, [[0, 1], [1, 2], [2, 3], [3, 4]], 0, 4], "expected": 4}, 
        {"args": [3, [[0, 1], [1, 2]], 1, 1], "expected": 0}   
    ]
    
    legends = [
        "Спроектируйте оптимальную маршрутизацию в сети дата-центров (BFS). Найдите минимальное количество переходов от стартового узла 0 до конечного 4. Ограничение O(V + E).",
        "Поиск кратчайшего пути обхода файрволов во внутренней корпоративной сети от узла 0 к 4. Избегайте зацикливаний. Сложность O(V + E)."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(n: int, edges: list[list[int]], start: int, target: int) -> int:",
            "examples": [{"args": [5, [[0, 1], [0, 2], [1, 3], [2, 4], [3, 4]], 0, 4], "expected": 2}],
            "tests": tests
        }
    }

@_add("be.code.dp_max_profit", "backend", 3, "Алгоритмы", "code")
def _(rng):
    # Задача: максимальная сумма не смежных элементов (House Robber)
    arr = [rng.randint(5, 25) for _ in range(6)]
    
    inc, exc = 0, 0
    for x in arr:
        inc, exc = exc + x, max(inc, exc)
    expected = max(inc, exc)
    
    tests = [
        {"args": [arr], "expected": expected},
        {"args": [[2, 7, 9, 3, 1]], "expected": 12}, # 2 + 9 + 1
        {"args": [[100, 1, 1, 100]], "expected": 200}
    ]
    
    legends = [
        "Спланируйте нагрузку на кластер. Вам дан массив пропускной способности узлов. Из-за архитектурных ограничений нельзя активировать два соседних узла. Найдите максимальную суммарную мощность.",
        "Выбор оптимальной стратегии в пошаговой игре. В массиве указано количество очков за захват баз. Захват соседних баз блокируется правилами. Вычислите максимальный счет (DP, сложность O(n))."
    ]
    
    return {
        "text": rng.choice(legends),
        "answer": None,
        "code": {
            "function_name": "solve", 
            "signature": "def solve(arr: list[int]) -> int:",
            "examples": [{"args": [[1, 2, 3, 1]], "expected": 4}],
            "tests": tests
        }
    }
