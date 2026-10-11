"""Проверка кода кандидата: решение не может подсмотреть правильные ответы или подделать зачёт."""
import pytest

from app.services.code_runner import run_tests

TESTS = [{"args": [1], "expected": 2}, {"args": [5], "expected": 10}]


@pytest.mark.parametrize("code", [
    # подсмотреть ожидаемый ответ через кадр стека обвязки
    'import statistics\ndef solve(x):\n    return statistics.sys._getframe(1).f_locals["test"]["expected"]\n',
    # добраться до os через «безопасный» модуль и напечатать поддельный результат
    'import statistics\ndef solve(x):\n    return 0\nstatistics.sys.modules["os"].write(1, b"{}")\n',
    'import collections\ndef solve(x):\n    return collections._sys.modules\n',
    'import statistics\ndef solve(x):\n    return statistics.random._os.getcwd()\n',
    'import re\ndef solve(x):\n    return re.enum.bltns.open\n',
    'from statistics import sys\ndef solve(x):\n    return 0\n',
    'from collections import _sys\ndef solve(x):\n    return 0\n',
])
def test_escape_attempts_are_rejected(code):
    res = run_tests(code, "solve", TESTS)
    assert res["passed"] == 0 and res["violations"], res


def test_forged_output_does_not_count():
    """Даже если решение напечатает «всё пройдено», зачёт считает основной процесс по своим ответам."""
    code = ('def solve(x):\n'
            '    print(\'{"passed": 2, "total": 2, "errors": []}\')\n'
            '    return -1\n')
    res = run_tests(code, "solve", TESTS)
    assert res["passed"] == 0 and res["total"] == 2


def test_child_never_receives_expected_answers(monkeypatch):
    import subprocess
    sent = {}
    real_run = subprocess.run

    def spy(*args, **kwargs):
        sent["input"] = kwargs.get("input", "")
        return real_run(*args, **kwargs)

    monkeypatch.setattr("app.services.code_runner.subprocess.run", spy)
    res = run_tests("def solve(x):\n    return x * 2\n", "solve", [{"args": [3], "expected": 987654}])
    assert res["passed"] == 0
    assert "987654" not in sent["input"] and "expected" not in sent["input"]


def test_honest_solutions_still_work():
    assert run_tests("def solve(x):\n    return x * 2\n", "solve", TESTS)["passed"] == 2
    with_class = ("class Node:\n    def __init__(self, v):\n        self._v = v\n        self.path = [v]\n"
                  "def solve(x):\n    n = Node(x)\n    return n._v * 2 + len(n.path) - 1\n")
    assert run_tests(with_class, "solve", TESTS)["passed"] == 2
    tuples = "def solve(x):\n    return (x * 2)\n"
    assert run_tests(tuples, "solve", TESTS)["passed"] == 2
    res = run_tests("def solve(x):\n    return 1 / 0\n", "solve", TESTS)
    assert res["passed"] == 0 and "ZeroDivisionError" in res["errors"][0]
