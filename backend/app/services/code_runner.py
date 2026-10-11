"""
Безопасная проверка кода кандидата на сервере.

Почему на сервере, а не только в браузере (Pyodide)?
  В браузере кандидат может подменить результат проверки — доверять ему нельзя.
  Pyodide на фронте — для удобства (кнопка «Запустить» с видимыми примерами),
  а ЗАЧЁТ ставит только сервер, на СКРЫТЫХ тестах.

Два барьера защиты:
  1. Статический анализ AST: запрещаем импорты (кроме безопасного списка),
     опасные функции (open, eval, exec, __import__...), «дандеры» (__class__ и т.п.)
     и пути к sys/os/builtins/кадрам стека (statistics.sys, random._os, enum.bltns, f_locals…).
  2. Запуск в отдельном процессе Python с таймаутом и лимитами CPU/памяти.
  3. Дочерний процесс получает только аргументы тестов, а правильные ответы и подсчёт зачёта
     остаются в основном процессе — их нельзя подсмотреть или подделать из кода решения.

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
# Атрибуты, через которые из «безопасных» модулей можно добраться до sys/os или до кадров стека
# (например, statistics.sys.modules["os"] или sys._getframe(1).f_locals). Решению задач они не нужны.
# Список модулей-атрибутов получен обходом всех модулей, достижимых из ALLOWED_IMPORTS (enum.bltns = builtins,
# random._os = os, collections._sys = sys, re._compiler… и т.д.).
FORBIDDEN_ATTRS = {"sys", "os", "modules", "builtins", "bltns", "subprocess", "system", "popen", "spawn", "fork",
                   "_sys", "_os", "_random", "_re", "_sre", "_string", "_compiler", "_constants", "_parser",
                   "_casefix", "_collections_abc", "_getframe", "_current_frames", "_exit",
                   "f_locals", "f_globals", "f_back", "f_builtins", "f_code", "f_trace",
                   "gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame", "tb_frame", "tb_next",
                   "settrace", "setprofile", "import_module", "loader", "stdin", "stdout", "stderr"}
FORBIDDEN_NAME_REFS = {"sys", "os", "builtins", "subprocess", "importlib"}
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
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAME_REFS:
            problems.append(f"Запрещённое имя: {node.id}")
        elif isinstance(node, ast.Attribute) and (node.attr in FORBIDDEN_ATTRS or node.attr.startswith("__")):
            problems.append(f"Запрещённый атрибут: {node.attr}")
        elif isinstance(node, ast.alias) and (node.name in FORBIDDEN_ATTRS or node.name.startswith("_")):
            problems.append(f"Запрещённый импорт: {node.name}")  # from statistics import sys / _sys
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


def _same(got, expected) -> bool:
    try:
        return got == json.loads(json.dumps(expected))
    except (TypeError, ValueError):
        return False


def run_tests(code: str, function_name: str, tests: list[dict]) -> dict:
    """
    Прогоняет код на тестах. Возвращает:
      {"passed": 4, "total": 6, "errors": [...], "violations": [...]}

    В дочерний процесс уходят только аргументы тестов. Ожидаемые ответы остаются здесь,
    и сравнение делает этот (основной) процесс — подделать результат из кода кандидата нельзя.
    """
    total = len(tests)
    violations = static_check(code, function_name)
    if violations:
        return {"passed": 0, "total": total, "errors": [], "violations": violations}
    payload = json.dumps({"code": code, "func": function_name, "args": [t["args"] for t in tests]})
    kwargs = {}
    if sys.platform != "win32":
        kwargs["preexec_fn"] = _limits
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(_HARNESS)], input=payload, capture_output=True, text=True,
            timeout=settings.code_exec_timeout_seconds, env={}, **kwargs,
        )
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        results = out["results"]
        if not isinstance(results, list):
            raise TypeError
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": total, "errors": ["Превышено время выполнения"], "violations": []}
    except (json.JSONDecodeError, IndexError, KeyError, TypeError):
        return {"passed": 0, "total": total, "errors": ["Решение аварийно завершилось"], "violations": []}
    if out.get("fatal"):
        return {"passed": 0, "total": total, "errors": [str(out["fatal"])[:200]], "violations": []}
    passed, errors = 0, []
    for i, test in enumerate(tests, 1):
        r = results[i - 1] if i <= len(results) and isinstance(results[i - 1], dict) else None
        if r is None:
            errors.append(f"Тест {i}: нет результата")
        elif not r.get("ok"):
            errors.append(f"Тест {i}: {str(r.get('error', 'Ошибка'))[:60]}")
        elif _same(r.get("value"), test["expected"]):
            passed += 1
        else:
            errors.append(f"Тест {i}: неверный ответ")
    return {"passed": passed, "total": total, "errors": errors[:5], "violations": []}
