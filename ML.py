import json
import json  # Используется для парсинга ответа LLM


# import gigachat # или любая другая библиотека для выбранного LLM API

import concurrent.futures


def execute_and_test(source_code: str, test_cases: list) -> dict:
    """
    Выполняет код кандидата на тестовых данных с ограничением по времени (1 секунда).
    test_cases - список словарей [{"input": (1, 2), "expected": 3}, ...]
    """
    # Создаем изолированное пространство имен, чтобы код кандидата не сломал нашу программу
    local_env = {}

    try:
        # Компилируем и загружаем функцию solve в local_env
        exec(source_code, {}, local_env)
        if "solve" not in local_env:
            return {"status": "error", "message": "Функция должна называться 'solve'"}

        solve_func = local_env["solve"]
    except Exception as e:
        return {"status": "error", "message": f"Ошибка компиляции: {e}"}

    passed_tests = 0
    total_tests = len(test_cases)

    # Функция для запуска одного теста
    def run_single_test(inputs):
        if isinstance(inputs, tuple):
            return solve_func(*inputs)
        return solve_func(inputs)

    # Запуск тестов с тайм-аутом
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for case in test_cases:
            future = executor.submit(run_single_test, case["input"])
            try:
                # Ждем максимум 1 секунду
                result = future.result(timeout=1.0)
                if result == case["expected"]:
                    passed_tests += 1
            except concurrent.futures.TimeoutError:
                return {"status": "failed", "message": "Тайм-аут (возможно бесконечный цикл)"}
            except Exception as e:
                return {"status": "failed", "message": f"Ошибка во время выполнения (Runtime Error): {e}"}

    return {
        "status": "success",
        "passed": passed_tests,
        "total": total_tests,
        "all_passed": passed_tests == total_tests
    }

class TaskMaskingEngine:
    def __init__(self):
        # База эталонных задач (инвариантов)
        self.invariants = {
            "sliding_window_1": {
                "math_core": "Дан массив целых чисел размера N и число K. Найти максимальную сумму подмассива размера K. Ограничение: O(n).",
                "inputs": "Массив целых чисел nums, целое число k",
                "outputs": "Целое число (максимальная сумма)"
            },
            "two_sum_1": {
                "math_core": "Дан массив чисел и целевое значение. Найти индексы двух чисел, дающих в сумме целевое значение. Ограничение: O(n).",
                "inputs": "Массив целых чисел nums, целое число target",
                "outputs": "Массив из двух целых чисел (индексы)"
            }
        }

    def generate_unique_task(self, task_id: str, context_theme: str = "кибербезопасность") -> dict:
        invariant = self.invariants.get(task_id)
        if not invariant:
            raise ValueError("Task ID не найден")

        user_prompt = f"""
        Измени легенду для этой задачи. Тематика новой легенды: {context_theme}.
        Суть алгоритма: {invariant['math_core']}
        Входные данные: {invariant['inputs']}
        Выходные данные: {invariant['outputs']}
        """

        # Здесь вызывается API вашей LLM (GigaChat, YandexGPT, OpenAI и т.д.)
        # response_text = llm_client.chat(system_prompt, user_prompt)

        # Заглушка для примера, эмулирующая ответ LLM
        response_text = """
        {
            "title": "Анализ DDoS-атаки",
            "description": "На сервер поступает поток пакетов. Дан массив размеров пакетов и окно времени K секунд. Найдите максимальный объем трафика, который прошел через сервер за любые непрерывные K секунд, чтобы настроить балансировщик.",
            "input_format": "Массив целых чисел (размеры пакетов) и целое число K (окно).",
            "output_format": "Одно целое число — пиковый объем трафика."
        }
        """

        return json.loads(response_text)


# Использование
engine = TaskMaskingEngine()
unique_task = engine.generate_unique_task("sliding_window_1", context_theme="анализ логов")
print(unique_task["title"])

import ast


class CodeComplexityInspector(ast.NodeVisitor):
    def __init__(self):
        self.current_loop_depth = 0
        self.max_loop_depth = 0
        self.forbidden_calls = []
        self.forbidden_imports = []

        # Список запрещенных библиотек для хардкорных алгоритмических задач
        self.restricted_modules = {"itertools", "math", "numpy", "pandas"}
        # Запрещенные методы (например, встроенная сортировка, если задача на сортировку)
        self.restricted_methods = {"sort", "sorted"}

    def visit_For(self, node):
        """Перехват цикла for"""
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)  # Идем глубже по дереву
        self.current_loop_depth -= 1

    def visit_While(self, node):
        """Перехват цикла while"""
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_Import(self, node):
        """Перехват импортов (import x)"""
        for alias in node.names:
            if alias.name in self.restricted_modules:
                self.forbidden_imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Перехват импортов (from x import y)"""
        if node.module in self.restricted_modules:
            self.forbidden_imports.append(node.module)
        self.generic_visit(node)

    def visit_Call(self, node):
        """Перехват вызовов функций (ищем встроенные чит-функции)"""
        if isinstance(node.func, ast.Name):
            if node.func.id in self.restricted_methods:
                self.forbidden_calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.restricted_methods:
                self.forbidden_calls.append(node.func.attr)
        self.generic_visit(node)

    def get_big_o_estimation(self) -> str:
        """Эвристическая оценка сложности на основе вложенности циклов"""
        if self.max_loop_depth == 0:
            return "O(1) или O(log n) (без циклов)"
        elif self.max_loop_depth == 1:
            return "O(n)"
        elif self.max_loop_depth == 2:
            return "O(n^2)"
        elif self.max_loop_depth == 3:
            return "O(n^3)"
        else:
            return f"O(n^{self.max_loop_depth})"


def evaluate_candidate_code(source_code: str, expected_complexity: int = 1) -> dict:
    """
    Основная функция проверки кода.
    expected_complexity: 1 для O(n), 2 для O(n^2) и т.д.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"status": "error", "message": f"Синтаксическая ошибка: {e}"}

    inspector = CodeComplexityInspector()
    inspector.visit(tree)

    is_cheating = len(inspector.forbidden_imports) > 0 or len(inspector.forbidden_calls) > 0
    complexity_passed = inspector.max_loop_depth <= expected_complexity

    score_penalty = 0
    if not complexity_passed:
        score_penalty -= 30  # Штраф за неоптимальное решение
    if is_cheating:
        score_penalty -= 100  # Обнуляем за использование чит-библиотек

    return {
        "status": "success",
        "estimated_complexity": inspector.get_big_o_estimation(),
        "max_loop_depth": inspector.max_loop_depth,
        "used_forbidden_imports": inspector.forbidden_imports,
        "used_forbidden_calls": inspector.forbidden_calls,
        "complexity_passed": complexity_passed,
        "penalty": score_penalty
    }


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===

# Кандидат 1: Пишет оптимально, но использует чит (sort)
code_candidate_1 = """
def solve(arr):
    arr.sort()
    return arr
"""

# Кандидат 2: Пишет неоптимально (O(n^2)), вложенные циклы
code_candidate_2 = """
def solve(arr, target):
    for i in range(len(arr)):
        for j in range(len(arr)):
            if arr[i] + arr[j] == target:
                return [i, j]
"""

# Кандидат 3: Пишет идеально (O(n)), использует хэш-таблицу
code_candidate_3 = """
def solve(arr, target):
    seen = {}
    for i, num in enumerate(arr):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
"""

print("Кандидат 2 (O(n^2)):", evaluate_candidate_code(code_candidate_2, expected_complexity=1))
print("Кандидат 3 (O(n)):", evaluate_candidate_code(code_candidate_3, expected_complexity=1))


def final_evaluation_pipeline(source_code: str, expected_complexity: int, test_cases: list):
    # ШАГ 1: Статический анализ (Анти-чит и оценка Big O)
    ast_result = evaluate_candidate_code(source_code, expected_complexity)
    if ast_result["status"] == "error":
        return {"final_score": 0, "details": "Синтаксическая ошибка"}

    if ast_result["penalty"] == -100:
        return {"final_score": 0, "details": "Обнаружено списывание или чит-библиотеки"}

    # ШАГ 2: Проверка математической правильности
    exec_result = execute_and_test(source_code, test_cases)
    if exec_result["status"] != "success" or not exec_result["all_passed"]:
        return {"final_score": 0, "details": "Тесты не пройдены или ошибка выполнения"}

    # ШАГ 3: Расчет финального балла
    # Если всё правильно, даем 100 баллов минус штраф за плохую оптимизацию
    final_score = 100 + ast_result["penalty"]

    return {
        "final_score": final_score,
        "complexity": ast_result["estimated_complexity"],
        "grade_confirmed": final_score >= 80  # Если решил неоптимально, получит 70 и грейд не подтвердится
    }


# --- Проверка работы конвейера ---
test_cases_two_sum = [
    {"input": ([2, 7, 11, 15], 9), "expected": [0, 1]},
    {"input": ([3, 2, 4], 6), "expected": [1, 2]}
]

# Кандидат написал правильное, но медленное решение O(n^2)
code = """
def solve(arr, target):
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] + arr[j] == target:
                return [i, j]
"""

print(final_evaluation_pipeline(code, expected_complexity=1, test_cases=test_cases_two_sum))
# Вывод будет: {'final_score': 70, 'complexity': 'O(n^2)', 'grade_confirmed': False}