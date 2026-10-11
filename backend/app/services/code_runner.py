"""
Безопасная проверка кода кандидата на сервере.

Почему на сервере, а не только в браузере (Pyodide)?
  В браузере кандидат может подменить результат проверки — доверять ему нельзя.
  Pyodide на фронте — для удобства (кнопка «Запустить» с видимыми примерами),
  а ЗАЧЁТ ставит только сервер, на СКРЫТЫХ тестах.

Два барьера защиты:
  1. Статический анализ AST: запрещаем импорты (кроме безопасного списка),
     опасные функции (open, eval, exec, __import__...) и обращения к «дандерам» (__class__ и т.п.).
  2. Запуск в отдельном процессе Python с таймаутом и лимитами CPU/памяти.

Для продакшена: запускать в изолированном контейнере (gVisor / Judge0 / nsjail).
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

from app.core.config import settings

ALLOWED_IMPORTS = {"math", "collections", "itertools", "functools", "heapq", "bisect", "re", "string", "statistics"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "globals", "locals", "vars",
                   "getattr", "setattr", "delattr", "breakpoint", "exit", "quit", "help", "memoryview", "__builtins__"}
MAX_CODE_LEN = 10_000

_HARNESS = Path(__file__).with_name("_code_harness.py")


def static_check(code: str, function_name: str) -> list[str]:
    """Возвращает список нарушений (пустой = код допустим)."""
    if len(code) > MAX_CODE_LEN:
        return ["Слишком длинное решение"]
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Синтаксическая ошибка: строка {e.lineno}: {e.msg}"]
    problems: list[str] = []
    defined = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    problems.append(f"Запрещённый импорт: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                problems.append(f"Запрещённый импорт: {node.module}")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            problems.append(f"Запрещённая функция: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            problems.append(f"Запрещённый атрибут: {node.attr}")
        elif isinstance(node, ast.FunctionDef) and node.name == function_name:
            defined = True
    if not defined:
        problems.append(f"Не найдена функция {function_name}")
    return sorted(set(problems))


def _limits():  # pragma: no cover — выполняется в дочернем процессе (только Linux/macOS)
    import resource
    cpu = int(settings.code_exec_timeout_seconds) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def run_tests(code: str, function_name: str, tests: list[dict]) -> dict:
    """
    Прогоняет код на тестах. Возвращает:
      {"passed": 4, "total": 6, "errors": [...], "violations": [...]}
    """
    violations = static_check(code, function_name)
    if violations:
        return {"passed": 0, "total": len(tests), "errors": [], "violations": violations}
    payload = json.dumps({"code": code, "func": function_name, "tests": tests})
    kwargs = {}
    if sys.platform != "win32":
        kwargs["preexec_fn"] = _limits
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(_HARNESS)], input=payload, capture_output=True, text=True,
            timeout=settings.code_exec_timeout_seconds, env={}, **kwargs,
        )
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": len(tests), "errors": ["Превышено время выполнения"], "violations": []}
    except (json.JSONDecodeError, IndexError):
        return {"passed": 0, "total": len(tests), "errors": ["Решение аварийно завершилось"], "violations": []}
    result["violations"] = []
    return result
