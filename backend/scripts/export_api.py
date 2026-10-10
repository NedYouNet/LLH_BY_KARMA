"""Сохраняет схему и таблицу маршрутов, не перезаписывая обзор API.

Запуск из backend/: python -m scripts.export_api.
"""
import json
from collections import defaultdict
from pathlib import Path
from app.main import app


def main() -> None:
    docs = Path(__file__).resolve().parents[2] / 'docs'
    docs.mkdir(exist_ok=True)
    spec = app.openapi()
    (docs / 'openapi.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    groups = defaultdict(list)
    for path, operations in spec['paths'].items():
        for method, operation in operations.items():
            if method not in {'get','post','put','patch','delete','head','options'}:
                continue
            tag = (operation.get('tags') or ['Прочее'])[0]
            auth = 'Да' if operation.get('security') else 'Нет'
            summary = operation.get('summary', '').replace('|', '\\|')
            groups[tag].append(f'| {method.upper()} | `{path}` | {summary} | {auth} |')
    lines = ['# Маршруты API', '', 'Сформировано из app.openapi(); тела запросов и ответов — в openapi.json и Swagger.', '']
    for tag, rows in groups.items():
        lines.extend([f'## {tag}', '', '| Метод | Путь | Назначение | Токен |','|---|---|---|---|', *rows, ''])
    (docs / 'api_routes.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'Схема и таблица: {sum(map(len, groups.values()))} маршрутов')


if __name__ == '__main__':
    main()
