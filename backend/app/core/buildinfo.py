"""
Идентификатор сборки для /api/health: по нему видно, КАКОЙ код на самом деле запущен.

Номер версии (1.4.0) меняется не на каждое исправление, а одинаковая версия не доказывает,
что контейнер пересобран. Поэтому health дополнительно показывает:
  - code      — отпечаток кода: SHA-256 от всех .py файлов бэкенда и requirements.txt (первые 12 символов).
                Переносы строк Windows (CRLF) приводятся к LF, поэтому у всех, у кого одинаковые файлы,
                отпечаток одинаковый — и на Windows, и в Docker, и на GitHub;
  - migration — какая миграция БД реально применена (таблица alembic_version).
Сравнить свой отпечаток с ожидаемым: python -m app.core.buildinfo (из папки backend).
"""
import hashlib
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]  # папка backend
PATTERNS = ("app/**/*.py", "alembic/**/*.py", "scripts/**/*.py", "requirements.txt")


def fingerprint_of(root: Path) -> str:
    h = hashlib.sha256()
    files = sorted({p for pattern in PATTERNS for p in root.glob(pattern)
                    if p.is_file() and "__pycache__" not in p.parts})
    for p in files:
        h.update(p.relative_to(root).as_posix().encode() + b"\0")
        h.update(p.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()[:12]


@lru_cache
def code_fingerprint() -> str:
    return fingerprint_of(ROOT)


def applied_migration(engine) -> str | None:
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:  # noqa: BLE001 — health не должен падать из-за этого (например, тестовая БД без Alembic)
        return None


if __name__ == "__main__":
    print(code_fingerprint())
