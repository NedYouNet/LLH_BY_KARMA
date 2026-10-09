import ast
import subprocess
import tempfile
import os


# --- 1. AST-Анализатор (Статическая оценка сложности) ---
def analyze_complexity(code_str: str) -> str:
    """Анализирует вложенность циклов для примерной оценки Big-O."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return "SyntaxError"

    max_depth = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            depth = 1
            # Проверяем наличие вложенных циклов
            for child in ast.walk(node):
                if isinstance(child, (ast.For, ast.While)) and child is not node:
                    depth = 2
                    break
            max_depth = max(max_depth, depth)

    if max_depth == 0:
        return "O(1) / O(log n)"
    elif max_depth == 1:
        return "O(n)"
    else:
        return "O(n^2) или хуже"


# --- 2. Изолированная песочница (MVP для Хакатона) ---
def run_code_in_sandbox(code: str, test_input: str, expected_output: str) -> dict:
    """
    Сохраняет код во временный файл и запускает как отдельный процесс.
    В продакшене здесь должен быть вызов Docker SDK.
    """
    # Добавляем принт инпута, чтобы код участника мог считать его через input()
    runner_code = f"""
import sys
# Перехват ввода
{code}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(runner_code)
        temp_file = f.name

    try:
        # Запускаем скрипт с жестким таймаутом в 1 секунду (Time Limit)
        result = subprocess.run(
            ['python3', temp_file],
            input=test_input,
            text=True,
            capture_output=True,
            timeout=1.0
        )
        os.remove(temp_file)

        output = result.stdout.strip()
        success = (output == str(expected_output))

        return {
            "success": success,
            "output": output,
            "error": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        os.remove(temp_file)
        return {"success": False, "output": "", "error": "Time Limit Exceeded (Tle)"}
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return {"success": False, "output": "", "error": str(e)}


# --- 3. Умный скоринг (Простая модель) ---
def calculate_candidate_score(tests_passed: int, total_tests: int, complexity: str, cv_grade: str) -> float:
    """Взвешивает результаты тестов, алгоритмическую сложность и релевантность резюме."""
    score = 0.0

    # 1. Прохождение скрытых тестов (вес 50 баллов)
    if total_tests > 0:
        score += (tests_passed / total_tests) * 50

    # 2. Оптимальность кода через AST (вес 30 баллов)
    if "O(n)" in complexity:
        score += 30
    elif "O(1)" in complexity:
        score += 30
    elif "O(n^2)" in complexity:
        score += 10  # Даем минимум за неоптимальное решение

    return round(score, 1)