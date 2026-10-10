"""
Шифрование персональных данных в базе (152-ФЗ: защита ПДн при хранении).

КАК ЭТО РАБОТАЕТ
  Колонки с ПДн (ФИО, телефон, Telegram, email для связи, текст резюме, контакты HR)
  объявлены в моделях типом `EncryptedText`. SQLAlchemy сам шифрует значение перед
  записью в БД и расшифровывает при чтении — остальной код работает с обычными строками.
  В самой базе лежит только шифротекст:  enc:v1:k1:Base64(nonce + ciphertext + tag)
  Если базу украдут (дамп, бэкап, доступ к серверу БД) — контакты не прочитать без ключа.

АЛГОРИТМ: AES-256-GCM (стандарт NIST, «аутентифицированное шифрование»):
  - каждый раз новый случайный nonce (12 байт) -> одинаковые телефоны дают разный шифротекст;
  - тег аутентификации: подменённый/испорченный шифротекст не расшифруется, а вызовет ошибку;
  - идентификатор ключа (k1) привязан к данным как AAD — нельзя «подсунуть» другой ключ.

КЛЮЧИ хранятся НЕ в базе, а в переменной окружения DATA_ENCRYPTION_KEYS:
    DATA_ENCRYPTION_KEYS="k2:<base64 32 байта>,k1:<старый ключ>"
  Первый ключ — текущий (им шифруем), остальные — только для чтения старых записей.
  Ротация: добавить новый ключ первым -> `python -m scripts.encryption rotate` перешифрует всё.
  Сгенерировать ключ:  python -m scripts.encryption gen-key

Для ГОСТ-шифрования (если потребуется по требованиям ФСП) достаточно заменить класс
FieldCipher — формат хранения с версией (v1) это позволяет.
"""
import base64
import hashlib
import logging
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

log = logging.getLogger("crypto")
PREFIX = "enc:v1:"


class DecryptionError(Exception):
    pass


class FieldCipher:
    def __init__(self, keys: dict[str, bytes], primary: str):
        for kid, key in keys.items():
            if len(key) != 32:
                raise ValueError(f"Ключ {kid}: нужно ровно 32 байта (AES-256), получено {len(key)}")
        self.keys = keys
        self.primary = primary

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ct = AESGCM(self.keys[self.primary]).encrypt(nonce, plaintext.encode("utf-8"), self.primary.encode())
        return f"{PREFIX}{self.primary}:{base64.b64encode(nonce + ct).decode()}"

    def decrypt(self, value: str) -> str:
        if not is_encrypted(value):
            return value  # старая запись до включения шифрования — отдаём как есть (миграция её зашифрует)
        try:
            kid, payload = value[len(PREFIX):].split(":", 1)
            raw = base64.b64decode(payload)
            key = self.keys[kid]
        except (ValueError, KeyError) as e:
            raise DecryptionError(f"Неизвестный ключ или битые данные: {e}") from None
        try:
            return AESGCM(key).decrypt(raw[:12], raw[12:], kid.encode()).decode("utf-8")
        except InvalidTag:
            raise DecryptionError("Данные повреждены или подменены (не прошла проверка целостности)") from None

    def needs_reencrypt(self, value: str) -> bool:
        return not is_encrypted(value) or not value.startswith(f"{PREFIX}{self.primary}:")


def is_encrypted(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def parse_keys(raw: str) -> tuple[dict[str, bytes], str]:
    keys: dict[str, bytes] = {}
    primary = ""
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        kid, b64 = part.split(":", 1)
        keys[kid.strip()] = base64.b64decode(b64.strip())
        primary = primary or kid.strip()
    return keys, primary


def _dev_key() -> bytes:
    return hashlib.sha256(b"fsp-talent-dev-data-key:" + settings.jwt_secret.encode()).digest()


@lru_cache
def get_cipher() -> FieldCipher:
    if settings.data_encryption_keys:
        keys, primary = parse_keys(settings.data_encryption_keys)
        if settings.environment != "prod":
            keys.setdefault("dev", _dev_key())  # вне продакшена читаем и данные, зашифрованные dev-ключом
        return FieldCipher(keys, primary)
    if settings.environment == "prod":
        raise RuntimeError("DATA_ENCRYPTION_KEYS не задан — в продакшене запуск без ключа шифрования запрещён")
    # Режим разработки: детерминированный ключ из JWT-секрета, чтобы данные переживали перезапуск
    log.warning("DATA_ENCRYPTION_KEYS не задан — используется dev-ключ. НЕ для продакшена!")
    return FieldCipher({"dev": _dev_key()}, "dev")


class EncryptedText(TypeDecorator):
    """Тип колонки: в Python — обычная строка, в БД — шифротекст AES-256-GCM."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return get_cipher().encrypt(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return get_cipher().decrypt(value)
