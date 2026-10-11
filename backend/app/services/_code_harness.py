"""
Обвязка, которая запускается в ОТДЕЛЬНОМ процессе и выполняет код кандидата.
Получает JSON на stdin, печатает JSON с результатом последней строкой stdout.
Этот файл не импортирует ничего из приложения — только стандартную библиотеку.
"""
import io
import json
import sys


def main() -> None:
    data = json.loads(sys.stdin.read())
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()  # глушим print() кандидата, чтобы он не сломал наш JSON
    passed, errors = 0, []
    try:
        namespace: dict = {}
        exec(compile(data["code"], "<solution>", "exec"), namespace)  # noqa: S102 — код уже прошёл AST-проверку
        func = namespace[data["func"]]
        for i, test in enumerate(data["tests"], 1):
            try:
                got = func(*json.loads(json.dumps(test["args"])))  # копия аргументов
                if isinstance(got, tuple):
                    got = list(got)
                if got == test["expected"]:
                    passed += 1
                else:
                    errors.append(f"Тест {i}: неверный ответ")
            except Exception as e:  # noqa: BLE001
                errors.append(f"Тест {i}: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"Ошибка выполнения: {type(e).__name__}")
    sys.stdout = real_stdout
    print(json.dumps({"passed": passed, "total": len(data["tests"]), "errors": errors[:5]}))


if __name__ == "__main__":
    main()
