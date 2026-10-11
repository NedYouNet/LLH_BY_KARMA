"""
Обвязка, которая запускается в ОТДЕЛЬНОМ процессе и выполняет код кандидата.

Получает на stdin JSON {"code", "func", "args"} — только АРГУМЕНТЫ тестов, без ожидаемых ответов.
Печатает последней строкой stdout JSON {"results": [...]} — что вернула функция кандидата на каждый тест.
Сравнение с правильными ответами делает основной процесс (code_runner.run_tests):
код кандидата не может ни подсмотреть ожидаемые значения, ни «нарисовать» себе зачёт.
Этот файл не импортирует ничего из приложения — только стандартную библиотеку.
"""
import io
import json
import sys


def _to_json(value):
    """Результат функции → JSON-совместимое значение (кортежи становятся списками)."""
    return json.loads(json.dumps(value, default=lambda o: list(o) if isinstance(o, (tuple, set, frozenset)) else repr(o)))


def main() -> None:
    data = json.loads(sys.stdin.read())
    args_list = data.pop("args")
    code, func_name = data["code"], data["func"]
    del data
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()  # глушим print() кандидата, чтобы он не сломал наш JSON
    results: list[dict] = []
    fatal = None
    try:
        namespace: dict = {}
        exec(compile(code, "<solution>", "exec"), namespace)  # noqa: S102 — код уже прошёл AST-проверку
        func = namespace[func_name]
        for args in args_list:
            try:
                got = func(*json.loads(json.dumps(args)))  # копия аргументов
                results.append({"ok": True, "value": _to_json(got)})
            except Exception as e:  # noqa: BLE001
                results.append({"ok": False, "error": type(e).__name__})
    except Exception as e:  # noqa: BLE001
        fatal = f"Ошибка выполнения: {type(e).__name__}"
    sys.stdout = real_stdout
    print(json.dumps({"results": results, "fatal": fatal}))


if __name__ == "__main__":
    main()
