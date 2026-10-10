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
# =====================================================================
# 🖥 ФРОНТЕНД-РАЗРАБОТКА
# =====================================================================
@_add("fe.code.0_easy_sum", "frontend", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(-10, 20) for _ in range(7)]
    tests = [{"args": [arr], "expected": sum(x for x in arr if x > 0)}, {"args": [[-1, 5]], "expected": 5}]
    return {"text": "Функция получает массив ширин DOM-элементов. Некоторые значения битые (отрицательные). Верните сумму только корректных (положительных) значений.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[-1, 5, 2]], "expected": 7}], "tests": tests}}

@_add("fe.code.0_mid_count", "frontend", 0, "Основы", "code")
def _(rng):
    logs = [rng.choice([200, 404, 500]) for _ in range(8)]
    tests = [{"args": [logs], "expected": logs.count(404)}, {"args": [[200, 200]], "expected": 0}]
    return {"text": "Проанализируйте массив ответов API на клиенте. Посчитайте, сколько раз встретилась ошибка 404.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[404, 200, 404]], "expected": 2}], "tests": tests}}

@_add("fe.code.0_hard_diff", "frontend", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(1, 50) for _ in range(6)]
    expected = max(abs(arr[i] - arr[i-1]) for i in range(1, len(arr))) if len(arr) > 1 else 0
    tests = [{"args": [arr], "expected": expected}, {"args": [[10, 10]], "expected": 0}]
    return {"text": "Для анимации найдите максимальный скачок (разницу по модулю) между соседними кадрами в массиве.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 10, 5]], "expected": 9}], "tests": tests}}

@_add("fe.code.1_easy_lookup", "frontend", 1, "Алгоритмы", "code")
def _(rng):
    arr = sorted(rng.sample(range(100), 7))
    target = rng.choice(arr)
    tests = [{"args": [arr, target], "expected": arr.index(target)}, {"args": [[1], 1], "expected": 0}]
    return {"text": "Дан отсортированный массив z-index слоев. Найдите индекс нужного слоя за O(log n).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], target: int) -> int:", "examples": [{"args": [[10, 20, 30], 20], "expected": 1}], "tests": tests}}

@_add("fe.code.1_mid_missing", "frontend", 1, "Алгоритмы", "code")
def _(rng):
    n = rng.randint(5, 10)
    missing = rng.randint(0, n)
    arr = [i for i in range(n + 1) if i != missing]
    rng.shuffle(arr)
    tests = [{"args": [arr], "expected": missing}, {"args": [[0, 1]], "expected": 2}]
    return {"text": "В форме Wizard пропущен один шаг из последовательности от 0 до N. Найдите номер пропущенного шага.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[3, 0, 1]], "expected": 2}], "tests": tests}}

@_add("fe.code.1_hard_anagram", "frontend", 1, "Структуры", "code")
def _(rng):
    tests = [{"args": ["active", "evitca"], "expected": 1}, {"args": ["btn", "nav"], "expected": 0}]
    return {"text": "Проверьте, состоят ли два CSS-класса из одинакового набора символов (анаграммы). 1 - да, 0 - нет.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(s1: str, s2: str) -> int:", "examples": [{"args": ["css", "ssc"], "expected": 1}], "tests": tests}}

@_add("fe.code.2_easy_unique", "frontend", 2, "Структуры", "code")
def _(rng):
    repeats = [rng.randint(1, 10) for _ in range(3)]
    arr = repeats + repeats + [rng.randint(11, 20)]
    rng.shuffle(arr)
    expected = next((x for x in arr if arr.count(x) == 1), -1)
    tests = [{"args": [arr], "expected": expected}, {"args": [[1, 1, 2, 2]], "expected": -1}]
    return {"text": "Найдите первый уникальный ID компонента в массиве рендеринга за O(n) с использованием Set/Map.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[4, 5, 4]], "expected": 5}], "tests": tests}}

@_add("fe.code.2_mid_stream", "frontend", 2, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(1, 20) for _ in range(8)]
    k = rng.randint(2, 4)
    expected = max(sum(arr[i:i+k]) for i in range(len(arr) - k + 1))
    tests = [{"args": [arr, k], "expected": expected}, {"args": [[1, 2], 2], "expected": 3}]
    return {"text": "Анализ FPS. Используя скользящее окно, найдите максимальную сумму задержек в окне размера K.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], k: int) -> int:", "examples": [{"args": [[1, 4, 2, 10, 2], 3], "expected": 16}], "tests": tests}}

@_add("fe.code.2_hard_intervals", "frontend", 2, "Оптимизация", "code")
def _(rng):
    tests = [{"args": [[[1, 4], [2, 5], [7, 9]]], "expected": 2}, {"args": [[[1, 2], [3, 4]]], "expected": 1}]
    return {"text": "Даны интервалы [start, end] времени показа тостов (уведомлений). Вычислите максимальное количество тостов на экране.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(intervals: list[list[int]]) -> int:", "examples": [{"args": [[[1, 5], [2, 3]]], "expected": 2}], "tests": tests}}

@_add("fe.code.3_easy_dp", "frontend", 3, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(5, 25) for _ in range(6)]
    inc, exc = 0, 0
    for x in arr: inc, exc = exc + x, max(inc, exc)
    tests = [{"args": [arr], "expected": max(inc, exc)}, {"args": [[2, 1, 1, 2]], "expected": 4}]
    return {"text": "Динамическое программирование. Дан массив весов компонентов. Нельзя лениво загружать два соседних. Найдите макс. вес.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 2, 3, 1]], "expected": 4}], "tests": tests}}

@_add("fe.code.3_mid_routing", "frontend", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [2, 3], [3, 4]], 0, 4], "expected": 4}, {"args": [3, [[0, 1]], 1, 1], "expected": 0}]
    return {"text": "Направленный граф React Router. Найдите минимальное количество переходов от стартового узла до конечного (BFS).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]], start: int, target: int) -> int:", "examples": [{"args": [3, [[0,1], [1,2]], 0, 2], "expected": 2}], "tests": tests}}

@_add("fe.code.3_hard_clusters", "frontend", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [3, 4]]], "expected": 2}, {"args": [3, []], "expected": 3}]
    return {"text": "Дана карта зависимостей NPM-пакетов. Верните количество независимых подграфов (связных компонент).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]]) -> int:", "examples": [{"args": [4, [[0, 1], [2, 3]]], "expected": 2}], "tests": tests}}

# =====================================================================
# 📊 DATA SCIENCE / ML
# =====================================================================
@_add("ds.code.0_easy_sum", "data_science", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(-10, 20) for _ in range(7)]
    tests = [{"args": [arr], "expected": sum(x for x in arr if x > 0)}, {"args": [[-1, 5]], "expected": 5}]
    return {"text": "Выполните очистку данных. Дан тензор фичей. Верните сумму только положительных значений, отфильтровав шум.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[-1, 5, 2]], "expected": 7}], "tests": tests}}

@_add("ds.code.0_mid_count", "data_science", 0, "Основы", "code")
def _(rng):
    logs = [rng.choice([-1, 0, 1]) for _ in range(8)]
    tests = [{"args": [logs], "expected": logs.count(-1)}, {"args": [[0, 0]], "expected": 0}]
    return {"text": "Посчитайте количество пропущенных значений (представленных как -1) в одномерном массиве признаков.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[-1, 0, -1]], "expected": 2}], "tests": tests}}

@_add("ds.code.0_hard_diff", "data_science", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(1, 50) for _ in range(6)]
    expected = max(abs(arr[i] - arr[i-1]) for i in range(1, len(arr))) if len(arr) > 1 else 0
    tests = [{"args": [arr], "expected": expected}, {"args": [[10, 10]], "expected": 0}]
    return {"text": "Для анализа Time Series данных найдите максимальное абсолютное отклонение между двумя соседними эпохами.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 10, 5]], "expected": 9}], "tests": tests}}

@_add("ds.code.1_easy_lookup", "data_science", 1, "Алгоритмы", "code")
def _(rng):
    arr = sorted(rng.sample(range(100), 7))
    target = rng.choice(arr)
    tests = [{"args": [arr, target], "expected": arr.index(target)}, {"args": [[1], 1], "expected": 0}]
    return {"text": "В отсортированном массиве весов (weights) найдите индекс целевого значения за O(log n).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], target: int) -> int:", "examples": [{"args": [[10, 20, 30], 20], "expected": 1}], "tests": tests}}

@_add("ds.code.1_mid_missing", "data_science", 1, "Алгоритмы", "code")
def _(rng):
    n = rng.randint(5, 10)
    missing = rng.randint(0, n)
    arr = [i for i in range(n + 1) if i != missing]
    rng.shuffle(arr)
    tests = [{"args": [arr], "expected": missing}, {"args": [[0, 1]], "expected": 2}]
    return {"text": "Интерполяция данных. В массиве уникальных индексов от 0 до N пропал один батч. Найдите его номер.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[3, 0, 1]], "expected": 2}], "tests": tests}}

@_add("ds.code.1_hard_anagram", "data_science", 1, "Структуры", "code")
def _(rng):
    tests = [{"args": ["cat", "tac"], "expected": 1}, {"args": ["dog", "god"], "expected": 1}, {"args": ["a", "b"], "expected": 0}]
    return {"text": "Проверьте, содержат ли два строковых тензора (категориальные метки) одинаковый набор символов. Верните 1 или 0.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(s1: str, s2: str) -> int:", "examples": [{"args": ["nlp", "pln"], "expected": 1}], "tests": tests}}

@_add("ds.code.2_easy_unique", "data_science", 2, "Структуры", "code")
def _(rng):
    repeats = [rng.randint(1, 10) for _ in range(3)]
    arr = repeats + repeats + [rng.randint(11, 20)]
    rng.shuffle(arr)
    expected = next((x for x in arr if arr.count(x) == 1), -1)
    tests = [{"args": [arr], "expected": expected}, {"args": [[1, 1, 2, 2]], "expected": -1}]
    return {"text": "Найдите первый уникальный выброс (outlier) в наборе данных за O(n) с использованием хэш-таблицы.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[4, 5, 4]], "expected": 5}], "tests": tests}}

@_add("ds.code.2_mid_stream", "data_science", 2, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(1, 20) for _ in range(8)]
    k = rng.randint(2, 4)
    expected = max(sum(arr[i:i+k]) for i in range(len(arr) - k + 1))
    tests = [{"args": [arr, k], "expected": expected}, {"args": [[1, 2], 2], "expected": 3}]
    return {"text": "Имитация 1D-свертки (Pooling). Найдите максимальную сумму подмассива фиксированного размера K.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], k: int) -> int:", "examples": [{"args": [[1, 4, 2, 10, 2], 3], "expected": 16}], "tests": tests}}

@_add("ds.code.2_hard_intervals", "data_science", 2, "Оптимизация", "code")
def _(rng):
    tests = [{"args": [[[1, 4], [2, 5], [7, 9]]], "expected": 2}, {"args": [[[1, 2], [3, 4]]], "expected": 1}]
    return {"text": "GPU-шедулинг. Дан массив временных интервалов обучения моделей. Вычислите макс. количество параллельных задач.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(intervals: list[list[int]]) -> int:", "examples": [{"args": [[[1, 5], [2, 3]]], "expected": 2}], "tests": tests}}

@_add("ds.code.3_easy_dp", "data_science", 3, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(5, 25) for _ in range(6)]
    inc, exc = 0, 0
    for x in arr: inc, exc = exc + x, max(inc, exc)
    tests = [{"args": [arr], "expected": max(inc, exc)}, {"args": [[2, 1, 1, 2]], "expected": 4}]
    return {"text": "Динамическое программирование (RL Reward). Максимизируйте сумму наград, избегая выбора двух смежных состояний.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 2, 3, 1]], "expected": 4}], "tests": tests}}

@_add("ds.code.3_mid_routing", "data_science", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [2, 3], [3, 4]], 0, 4], "expected": 4}, {"args": [3, [[0, 1]], 1, 1], "expected": 0}]
    return {"text": "Поиск кратчайшего пути в K-Nearest Neighbors графе. Верните минимальное количество шагов от start до target.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]], start: int, target: int) -> int:", "examples": [{"args": [3, [[0,1], [1,2]], 0, 2], "expected": 2}], "tests": tests}}

@_add("ds.code.3_hard_clusters", "data_science", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [3, 4]]], "expected": 2}, {"args": [3, []], "expected": 3}]
    return {"text": "Алгоритм кластеризации DBSCAN. Дан граф дистанций. Вычислите количество изолированных кластеров в наборе.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]]) -> int:", "examples": [{"args": [4, [[0, 1], [2, 3]]], "expected": 2}], "tests": tests}}

# =====================================================================
# 🧪 ТЕСТИРОВАНИЕ (QA)
# =====================================================================
@_add("qa.code.0_easy_sum", "qa", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(-10, 20) for _ in range(7)]
    tests = [{"args": [arr], "expected": sum(x for x in arr if x > 0)}, {"args": [[-1, 5]], "expected": 5}]
    return {"text": "Суммируйте время выполнения только успешных тест-кейсов (значения > 0). Упавшие тесты имеют код -1.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[-1, 5, 2]], "expected": 7}], "tests": tests}}

@_add("qa.code.0_mid_count", "qa", 0, "Основы", "code")
def _(rng):
    logs = [rng.choice([1, 0]) for _ in range(8)]
    tests = [{"args": [logs], "expected": logs.count(0)}, {"args": [[1, 1]], "expected": 0}]
    return {"text": "Вам дан лог CI/CD, где 1 - тест пройден, 0 - провален. Подсчитайте количество проваленных автотестов.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 0, 0]], "expected": 2}], "tests": tests}}

@_add("qa.code.0_hard_diff", "qa", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(1, 50) for _ in range(6)]
    expected = max(abs(arr[i] - arr[i-1]) for i in range(1, len(arr))) if len(arr) > 1 else 0
    tests = [{"args": [arr], "expected": expected}, {"args": [[10, 10]], "expected": 0}]
    return {"text": "Выявите Flaky-тесты. Найдите максимальную разницу во времени ответа между двумя последовательными прогонами.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 10, 5]], "expected": 9}], "tests": tests}}

@_add("qa.code.1_easy_lookup", "qa", 1, "Алгоритмы", "code")
def _(rng):
    arr = sorted(rng.sample(range(100), 7))
    target = rng.choice(arr)
    tests = [{"args": [arr, target], "expected": arr.index(target)}, {"args": [[1], 1], "expected": 0}]
    return {"text": "В отсортированном массиве ID дефектов найдите индекс нужного бага за O(log n).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], target: int) -> int:", "examples": [{"args": [[10, 20, 30], 20], "expected": 1}], "tests": tests}}

@_add("qa.code.1_mid_missing", "qa", 1, "Алгоритмы", "code")
def _(rng):
    n = rng.randint(5, 10)
    missing = rng.randint(0, n)
    arr = [i for i in range(n + 1) if i != missing]
    rng.shuffle(arr)
    tests = [{"args": [arr], "expected": missing}, {"args": [[0, 1]], "expected": 2}]
    return {"text": "Система потеряла один чек-лист. В массиве уникальных номеров от 0 до N не хватает одного. Найдите его.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[3, 0, 1]], "expected": 2}], "tests": tests}}

@_add("qa.code.1_hard_anagram", "qa", 1, "Структуры", "code")
def _(rng):
    tests = [{"args": ["status", "sutats"], "expected": 1}, {"args": ["bug", "fix"], "expected": 0}]
    return {"text": "Сравните ключи JSON. Проверьте, являются ли две строки анаграммами (состоят из одних букв). Верните 1 или 0.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(s1: str, s2: str) -> int:", "examples": [{"args": ["json", "nosj"], "expected": 1}], "tests": tests}}

@_add("qa.code.2_easy_unique", "qa", 2, "Структуры", "code")
def _(rng):
    repeats = [rng.randint(1, 10) for _ in range(3)]
    arr = repeats + repeats + [rng.randint(11, 20)]
    rng.shuffle(arr)
    expected = next((x for x in arr if arr.count(x) == 1), -1)
    tests = [{"args": [arr], "expected": expected}, {"args": [[1, 1, 2, 2]], "expected": -1}]
    return {"text": "Найдите первый уникальный номер ошибки (error code) в логах нагрузочного тестирования.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[4, 5, 4]], "expected": 5}], "tests": tests}}

@_add("qa.code.2_mid_stream", "qa", 2, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(1, 20) for _ in range(8)]
    k = rng.randint(2, 4)
    expected = max(sum(arr[i:i+k]) for i in range(len(arr) - k + 1))
    tests = [{"args": [arr, k], "expected": expected}, {"args": [[1, 2], 2], "expected": 3}]
    return {"text": "Нагрузочное тестирование (JMeter). Вычислите пиковую сумму запросов в скользящем окне размера K.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], k: int) -> int:", "examples": [{"args": [[1, 4, 2, 10, 2], 3], "expected": 16}], "tests": tests}}

@_add("qa.code.2_hard_intervals", "qa", 2, "Оптимизация", "code")
def _(rng):
    tests = [{"args": [[[1, 4], [2, 5], [7, 9]]], "expected": 2}, {"args": [[[1, 2], [3, 4]]], "expected": 1}]
    return {"text": "Анализ параллельных тест-сьютов. По массиву времени [start, end] найдите максимальное число одновременно идущих тестов.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(intervals: list[list[int]]) -> int:", "examples": [{"args": [[[1, 5], [2, 3]]], "expected": 2}], "tests": tests}}

@_add("qa.code.3_easy_dp", "qa", 3, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(5, 25) for _ in range(6)]
    inc, exc = 0, 0
    for x in arr: inc, exc = exc + x, max(inc, exc)
    tests = [{"args": [arr], "expected": max(inc, exc)}, {"args": [[2, 1, 1, 2]], "expected": 4}]
    return {"text": "DP-планировщик расписания тестов. Найдите максимальное покрытие, если нельзя запускать соседние по списку модули.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 2, 3, 1]], "expected": 4}], "tests": tests}}

@_add("qa.code.3_mid_routing", "qa", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [2, 3], [3, 4]], 0, 4], "expected": 4}, {"args": [3, [[0, 1]], 1, 1], "expected": 0}]
    return {"text": "Тестирование конечного автомата (State Machine). Найдите минимальное количество переходов до статуса target.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]], start: int, target: int) -> int:", "examples": [{"args": [3, [[0,1], [1,2]], 0, 2], "expected": 2}], "tests": tests}}

@_add("qa.code.3_hard_clusters", "qa", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [3, 4]]], "expected": 2}, {"args": [3, []], "expected": 3}]
    return {"text": "Поиск Deadlock-ов. Дана карта взаимных блокировок. Вычислите количество изолированных кластеров (групп потоков).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]]) -> int:", "examples": [{"args": [4, [[0, 1], [2, 3]]], "expected": 2}], "tests": tests}}

# =====================================================================
# ⚙️ DEVOPS / SRE
# =====================================================================
@_add("do.code.0_easy_sum", "devops", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(-10, 20) for _ in range(7)]
    tests = [{"args": [arr], "expected": sum(x for x in arr if x > 0)}, {"args": [[-1, 5]], "expected": 5}]
    return {"text": "Суммируйте доступную память на узлах. Игнорируйте отрицательные значения (отключенные узлы).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[-1, 5, 2]], "expected": 7}], "tests": tests}}

@_add("do.code.0_mid_count", "devops", 0, "Основы", "code")
def _(rng):
    logs = [rng.choice([0, 1]) for _ in range(8)]
    tests = [{"args": [logs], "expected": logs.count(1)}, {"args": [[0, 0]], "expected": 0}]
    return {"text": "В массиве статусов подов Kubernetes (1 - OOMKilled, 0 - Running) посчитайте количество падений (1).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 0, 1]], "expected": 2}], "tests": tests}}

@_add("do.code.0_hard_diff", "devops", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(1, 50) for _ in range(6)]
    expected = max(abs(arr[i] - arr[i-1]) for i in range(1, len(arr))) if len(arr) > 1 else 0
    tests = [{"args": [arr], "expected": expected}, {"args": [[10, 10]], "expected": 0}]
    return {"text": "Мониторинг CPU. Найдите максимальный скачок нагрузки (разница по модулю) между двумя последовательными замерами.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 10, 5]], "expected": 9}], "tests": tests}}

@_add("do.code.1_easy_lookup", "devops", 1, "Алгоритмы", "code")
def _(rng):
    arr = sorted(rng.sample(range(100), 7))
    target = rng.choice(arr)
    tests = [{"args": [arr, target], "expected": arr.index(target)}, {"args": [[1], 1], "expected": 0}]
    return {"text": "В отсортированном списке открытых портов фаервола найдите индекс нужного порта (Бинарный поиск).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], target: int) -> int:", "examples": [{"args": [[10, 20, 30], 20], "expected": 1}], "tests": tests}}

@_add("do.code.1_mid_missing", "devops", 1, "Алгоритмы", "code")
def _(rng):
    n = rng.randint(5, 10)
    missing = rng.randint(0, n)
    arr = [i for i in range(n + 1) if i != missing]
    rng.shuffle(arr)
    tests = [{"args": [arr], "expected": missing}, {"args": [[0, 1]], "expected": 2}]
    return {"text": "В кластере пропал один сервер. В массиве уникальных ID от 0 до N найдите пропущенный.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[3, 0, 1]], "expected": 2}], "tests": tests}}

@_add("do.code.1_hard_anagram", "devops", 1, "Структуры", "code")
def _(rng):
    tests = [{"args": ["prod", "dorp"], "expected": 1}, {"args": ["dev", "qa"], "expected": 0}]
    return {"text": "Сравните хэши конфигов. Проверьте, являются ли две строки анаграммами. Верните 1 (да) или 0 (нет).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(s1: str, s2: str) -> int:", "examples": [{"args": ["sh", "hs"], "expected": 1}], "tests": tests}}

@_add("do.code.2_easy_unique", "devops", 2, "Структуры", "code")
def _(rng):
    repeats = [rng.randint(1, 10) for _ in range(3)]
    arr = repeats + repeats + [rng.randint(11, 20)]
    rng.shuffle(arr)
    expected = next((x for x in arr if arr.count(x) == 1), -1)
    tests = [{"args": [arr], "expected": expected}, {"args": [[1, 1, 2, 2]], "expected": -1}]
    return {"text": "Найдите первый уникальный IP-адрес злоумышленника в логах балансировщика за O(n).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[4, 5, 4]], "expected": 5}], "tests": tests}}

@_add("do.code.2_mid_stream", "devops", 2, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(1, 20) for _ in range(8)]
    k = rng.randint(2, 4)
    expected = max(sum(arr[i:i+k]) for i in range(len(arr) - k + 1))
    tests = [{"args": [arr, k], "expected": expected}, {"args": [[1, 2], 2], "expected": 3}]
    return {"text": "Rate Limiting. Найдите пиковый объем трафика в скользящем окне размера K.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], k: int) -> int:", "examples": [{"args": [[1, 4, 2, 10, 2], 3], "expected": 16}], "tests": tests}}

@_add("do.code.2_hard_intervals", "devops", 2, "Оптимизация", "code")
def _(rng):
    tests = [{"args": [[[1, 4], [2, 5], [7, 9]]], "expected": 2}, {"args": [[[1, 2], [3, 4]]], "expected": 1}]
    return {"text": "Анализ CI/CD пайплайнов. По массиву [start, end] вычислите максимальное количество одновременно работающих runner-ов.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(intervals: list[list[int]]) -> int:", "examples": [{"args": [[[1, 5], [2, 3]]], "expected": 2}], "tests": tests}}

@_add("do.code.3_easy_dp", "devops", 3, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(5, 25) for _ in range(6)]
    inc, exc = 0, 0
    for x in arr: inc, exc = exc + x, max(inc, exc)
    tests = [{"args": [arr], "expected": max(inc, exc)}, {"args": [[2, 1, 1, 2]], "expected": 4}]
    return {"text": "Оптимизация ресурсов (DP). Найдите макс. мощность, если из-за тепловыделения нельзя запускать серверы в соседних стойках.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 2, 3, 1]], "expected": 4}], "tests": tests}}

@_add("do.code.3_mid_routing", "devops", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [2, 3], [3, 4]], 0, 4], "expected": 4}, {"args": [3, [[0, 1]], 1, 1], "expected": 0}]
    return {"text": "Топология сети. Найдите кратчайший маршрут (число хопов) между свичами start и target с помощью BFS.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]], start: int, target: int) -> int:", "examples": [{"args": [3, [[0,1], [1,2]], 0, 2], "expected": 2}], "tests": tests}}

@_add("do.code.3_hard_clusters", "devops", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [3, 4]]], "expected": 2}, {"args": [3, []], "expected": 3}]
    return {"text": "Анализ Blast Radius (радиус поражения). Вычислите количество изолированных подсетей в случае разрыва линков.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]]) -> int:", "examples": [{"args": [4, [[0, 1], [2, 3]]], "expected": 2}], "tests": tests}}
    # =====================================================================
# ⚙️ БЭКЕНД-РАЗРАБОТКА
# =====================================================================
@_add("be.code.0_easy_sum", "backend", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(-10, 20) for _ in range(7)]
    tests = [{"args": [arr], "expected": sum(x for x in arr if x > 0)}, {"args": [[-1, 5]], "expected": 5}]
    return {"text": "Напишите функцию, которая вернет сумму всех положительных элементов массива (симуляция фильтрации валидных ID).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[-1, 5, 2]], "expected": 7}], "tests": tests}}

@_add("be.code.0_mid_count", "backend", 0, "Основы", "code")
def _(rng):
    logs = [rng.choice([200, 404, 500]) for _ in range(8)]
    tests = [{"args": [logs], "expected": logs.count(500)}, {"args": [[200, 200]], "expected": 0}]
    return {"text": "Вам дан лог HTTP-статусов ответа сервера. Подсчитайте количество критических ошибок (статус 500).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[500, 200, 500]], "expected": 2}], "tests": tests}}

@_add("be.code.0_hard_diff", "backend", 0, "Основы", "code")
def _(rng):
    arr = [rng.randint(1, 50) for _ in range(6)]
    expected = max(abs(arr[i] - arr[i-1]) for i in range(1, len(arr))) if len(arr) > 1 else 0
    tests = [{"args": [arr], "expected": expected}, {"args": [[10, 10]], "expected": 0}]
    return {"text": "Анализ времени ответа БД. Найдите максимальную разницу (по модулю) между двумя соседними запросами в массиве.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 10, 5]], "expected": 9}], "tests": tests}}

@_add("be.code.1_easy_lookup", "backend", 1, "Алгоритмы", "code")
def _(rng):
    arr = sorted(rng.sample(range(100), 7))
    target = rng.choice(arr)
    tests = [{"args": [arr, target], "expected": arr.index(target)}, {"args": [[1], 1], "expected": 0}]
    return {"text": "Дан отсортированный массив ID пользователей. Найдите индекс нужного пользователя. Ожидаемая сложность O(log n).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], target: int) -> int:", "examples": [{"args": [[10, 20, 30], 20], "expected": 1}], "tests": tests}}

@_add("be.code.1_mid_missing", "backend", 1, "Алгоритмы", "code")
def _(rng):
    n = rng.randint(5, 10)
    missing = rng.randint(0, n)
    arr = [i for i in range(n + 1) if i != missing]
    rng.shuffle(arr)
    tests = [{"args": [arr], "expected": missing}, {"args": [[0, 1]], "expected": 2}]
    return {"text": "В базе данных нарушился Sequence. В массиве уникальных ID от 0 до N пропущено одно значение. Найдите его.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[3, 0, 1]], "expected": 2}], "tests": tests}}

@_add("be.code.1_hard_anagram", "backend", 1, "Структуры", "code")
def _(rng):
    tests = [{"args": ["listen", "silent"], "expected": 1}, {"args": ["rat", "car"], "expected": 0}]
    return {"text": "Сравнение токенов. Проверьте, являются ли две строки анаграммами (состоят из одного набора символов). 1 - да, 0 - нет.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(s1: str, s2: str) -> int:", "examples": [{"args": ["abc", "cba"], "expected": 1}], "tests": tests}}

@_add("be.code.2_easy_unique", "backend", 2, "Структуры", "code")
def _(rng):
    repeats = [rng.randint(1, 10) for _ in range(3)]
    arr = repeats + repeats + [rng.randint(11, 20)]
    rng.shuffle(arr)
    expected = next((x for x in arr if arr.count(x) == 1), -1)
    tests = [{"args": [arr], "expected": expected}, {"args": [[1, 1, 2, 2]], "expected": -1}]
    return {"text": "Поиск коллизий. Найдите первый уникальный элемент массива за O(n) с использованием хэш-таблицы.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[4, 5, 4]], "expected": 5}], "tests": tests}}

@_add("be.code.2_mid_stream", "backend", 2, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(1, 20) for _ in range(8)]
    k = rng.randint(2, 4)
    expected = max(sum(arr[i:i+k]) for i in range(len(arr) - k + 1))
    tests = [{"args": [arr, k], "expected": expected}, {"args": [[1, 2], 2], "expected": 3}]
    return {"text": "Обработка потока. Используя скользящее окно, найдите максимальную сумму входящих байт в окне размера K.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int], k: int) -> int:", "examples": [{"args": [[1, 4, 2, 10, 2], 3], "expected": 16}], "tests": tests}}

@_add("be.code.2_hard_intervals", "backend", 2, "Оптимизация", "code")
def _(rng):
    tests = [{"args": [[[1, 4], [2, 5], [7, 9]]], "expected": 2}, {"args": [[[1, 2], [3, 4]]], "expected": 1}]
    return {"text": "Управление сессиями. Дан массив временных интервалов [start, end]. Вычислите макс. количество одновременно активных сессий.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(intervals: list[list[int]]) -> int:", "examples": [{"args": [[[1, 5], [2, 3]]], "expected": 2}], "tests": tests}}

@_add("be.code.3_easy_dp", "backend", 3, "Алгоритмы", "code")
def _(rng):
    arr = [rng.randint(5, 25) for _ in range(6)]
    inc, exc = 0, 0
    for x in arr: inc, exc = exc + x, max(inc, exc)
    tests = [{"args": [arr], "expected": max(inc, exc)}, {"args": [[2, 1, 1, 2]], "expected": 4}]
    return {"text": "Динамическое программирование. Дан массив мощностей узлов. Найдите макс. сумму, если нельзя активировать два соседних.", "answer": None, "code": {"function_name": "solve", "signature": "def solve(arr: list[int]) -> int:", "examples": [{"args": [[1, 2, 3, 1]], "expected": 4}], "tests": tests}}

@_add("be.code.3_mid_routing", "backend", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [2, 3], [3, 4]], 0, 4], "expected": 4}, {"args": [3, [[0, 1]], 1, 1], "expected": 0}]
    return {"text": "Направленный граф микросервисов. Найдите минимальное количество переходов (хопов) от start до target (BFS).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]], start: int, target: int) -> int:", "examples": [{"args": [3, [[0,1], [1,2]], 0, 2], "expected": 2}], "tests": tests}}

@_add("be.code.3_hard_clusters", "backend", 3, "Графы", "code")
def _(rng):
    tests = [{"args": [5, [[0, 1], [1, 2], [3, 4]]], "expected": 2}, {"args": [3, []], "expected": 3}]
    return {"text": "Шардирование БД. Дан граф узлов и связей. Верните количество изолированных кластеров (связных компонент).", "answer": None, "code": {"function_name": "solve", "signature": "def solve(n: int, edges: list[list[int]]) -> int:", "examples": [{"args": [4, [[0, 1], [2, 3]]], "expected": 2}], "tests": tests}}
