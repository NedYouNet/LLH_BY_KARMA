"""
Инструменты для ключей шифрования персональных данных.

  python -m scripts.encryption gen-key   # сгенерировать новый ключ AES-256 для DATA_ENCRYPTION_KEYS
  python -m scripts.encryption rotate    # перешифровать все ПДн текущим (первым) ключом
  python -m scripts.encryption check     # показать, сколько значений зашифровано каким ключом

Ротация ключа (раз в год или при подозрении на утечку):
  1) gen-key -> добавить новый ключ ПЕРВЫМ:  DATA_ENCRYPTION_KEYS="k2:<новый>,k1:<старый>"
  2) перезапустить бэкенд (читает и старые, и новые записи)
  3) rotate -> все записи перешифрованы ключом k2
  4) убрать k1 из переменной
"""
import base64
import os
import sys
from collections import Counter

from sqlalchemy import inspect, text

from app.core.crypto import EncryptedText, get_cipher, is_encrypted
from app.core.database import Base, engine
import app.models  # noqa: F401


def encrypted_columns(conn=None) -> dict[str, list[str]]:
    """Все колонки моделей с типом EncryptedText: {таблица: [колонки]}.

    Если передано соединение, берём только колонки, которые уже есть в БД:
    миграция 0003 запускается, когда более поздних колонок (например, employer_profiles.contact из 0004) ещё нет.
    """
    existing = None
    if conn is not None:
        insp = inspect(conn)
        existing = {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}
    out: dict[str, list[str]] = {}
    for table in Base.metadata.sorted_tables:
        cols = [c.name for c in table.columns if isinstance(c.type, EncryptedText)]
        if existing is not None:
            cols = [c for c in cols if c in existing.get(table.name, set())]
        if cols:
            out[table.name] = cols
    return out


def reencrypt(conn, decrypt_only: bool = False) -> int:
    """Шифрует открытые значения и перешифровывает старым ключом зашифрованные. Возвращает число изменений."""
    cipher = get_cipher()
    changed = 0
    for table, cols in encrypted_columns(conn).items():
        rows = conn.execute(text(f"SELECT id, {', '.join(cols)} FROM {table}")).mappings().all()
        for row in rows:
            updates = {}
            for col in cols:
                val = row[col]
                if val is None:
                    continue
                if decrypt_only:
                    if is_encrypted(val):
                        updates[col] = cipher.decrypt(val)
                elif cipher.needs_reencrypt(val):
                    updates[col] = cipher.encrypt(cipher.decrypt(val))
            if updates:
                sets = ", ".join(f"{c} = :{c}" for c in updates)
                conn.execute(text(f"UPDATE {table} SET {sets} WHERE id = :id"), {**updates, "id": row["id"]})
                changed += 1
    return changed


def main(cmd: str) -> None:
    if cmd == "gen-key":
        print("k" + base64.b16encode(os.urandom(2)).decode().lower() + ":" + base64.b64encode(os.urandom(32)).decode())
    elif cmd == "rotate":
        with engine.begin() as conn:
            print(f"Перешифровано строк: {reencrypt(conn)}")
    elif cmd == "check":
        stats: Counter = Counter()
        with engine.connect() as conn:
            for table, cols in encrypted_columns(conn).items():
                for row in conn.execute(text(f"SELECT {', '.join(cols)} FROM {table}")):
                    for v in row:
                        if v is not None:
                            stats["открытый текст!" if not is_encrypted(v) else v.split(":")[2]] += 1
        print(dict(stats) or "ПДн в базе нет")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
