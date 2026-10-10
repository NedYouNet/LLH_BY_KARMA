"""
Интеграция с реестром ФСП.

API ФСП в рамках хакатона НЕ предоставляется, поэтому реестр собран из двух источников:
  - `FileFspRegistry` — НАСТОЯЩИЕ результаты соревнований из таблицы (data/fsp_results.xlsx),
    собранные вручную из открытых протоколов. Такие достижения помечаются verified;
  - `MockFspRegistry` — детерминированная заглушка для демо: по одному и тому же ID всегда
    возвращает одни и те же достижения, помеченные demo;
  - `CombinedFspRegistry` — сначала ищет ID в таблице, потом (если разрешено) в заглушке.
`FspRegistryClient` — интерфейс. В продакшене пишем `HttpFspRegistry`, который ходит в реальный
API ФСП с токеном сервисного аккаунта Keycloak, — остальной код менять не придётся.

Правила заглушки (их стоит знать для демо):
  - ID — 6 цифр (100000–999999), иначе «не найден»;
  - ID, оканчивающийся на 0 — участник есть, но соревнований нет (проверяем кейс «без истории»);
  - иначе — от 1 до 5 соревнований.
"""
import logging
import math
import random
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.services.fsp_data import LEVEL_NAME, FspDataset, load_dataset

log = logging.getLogger("fsp")
BACKEND_DIR = Path(__file__).resolve().parents[2]

_DISCIPLINES = ["Продуктовое программирование", "Алгоритмическое программирование",
                "Программирование систем информационной безопасности", "Программирование БАС",
                "Программирование робототехники"]
_EVENTS = [("Чемпионат России по спортивному программированию", "all_russian"),
           ("Кубок России по спортивному программированию", "all_russian"),
           ("Всероссийский хакатон ФСП", "all_russian"),
           ("Международные соревнования «Цифровые горизонты»", "international"),
           ("Региональный этап Чемпионата России", "regional"),
           ("Городской турнир по программированию", "municipal")]


class FspRegistryClient(Protocol):
    def get_participant(self, fsp_id: str) -> dict | None: ...


class MockFspRegistry:
    def get_participant(self, fsp_id: str) -> dict | None:
        if not (fsp_id.isdigit() and len(fsp_id) == 6):
            return None
        rng = random.Random(f"fsp:{fsp_id}")
        if fsp_id.endswith("0"):
            return {"fsp_id": fsp_id, "achievements": [], "rating": None, "sport_rank": None, "source": "demo"}
        achievements = []
        for _ in range(rng.randint(1, 5)):
            event, level = rng.choice(_EVENTS)
            place = rng.choices([1, 2, 3, None], weights=[1, 2, 3, 6])[0]
            achievements.append({
                "event": event,
                "discipline": rng.choice(_DISCIPLINES),
                "level": level,
                "level_name": LEVEL_NAME[level],
                "year": rng.randint(2021, 2026),
                "place": place,  # None = участник/финалист без призового места
                "result": f"{place} место" if place else rng.choice(["Финалист", "Участник"]),
                "team": rng.choice([None, "Команда «Байт»", "Команда «Стек»", "Команда «Рекурсия»"]),
                "source": "fsp_registry_demo",     # заглушка, а не настоящий реестр
                "verification_status": "demo",     # в бою: "verified" после проверки через API ФСП
                "verified": False,
            })
        achievements.sort(key=lambda a: -a["year"])
        prizes = sum(1 for a in achievements if a["place"])
        sport_rank = rng.choice([None, "3 разряд", "2 разряд"]) if not prizes else \
            rng.choice(["1 разряд", "КМС"] if prizes < 3 else ["КМС", "МС"])
        return {"fsp_id": fsp_id, "achievements": achievements, "rating": rng.randint(1000, 2400),
                "sport_rank": sport_rank, "source": "demo"}


class FileFspRegistry:
    """Реальные результаты из таблицы. Перечитывает файл, если он изменился, — перезапуск не нужен."""

    def __init__(self, path: str | Path):
        path = Path(path)
        self.path = path if path.is_absolute() else BACKEND_DIR / path
        self._mtime: float | None = None
        self._data = FspDataset()

    def dataset(self) -> FspDataset:
        try:
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            self._mtime, self._data = None, FspDataset()
            return self._data
        if mtime != self._mtime:
            try:
                self._data = load_dataset(self.path)
                for err in self._data.errors:
                    log.warning("Таблица ФСП %s: %s", self.path.name, err)
            except Exception as e:  # битый файл не должен ронять API — работаем без него
                log.error("Не удалось прочитать таблицу ФСП %s: %s", self.path, e)
                self._data = FspDataset(errors=[str(e)])
            self._mtime = mtime
        return self._data

    def get_participant(self, fsp_id: str) -> dict | None:
        ds = self.dataset()
        achievements = ds.participants.get(fsp_id.strip())
        if achievements is None:
            return None
        return {"fsp_id": fsp_id.strip(), "achievements": [dict(a) for a in achievements], "rating": None,
                "sport_rank": ds.ranks.get(fsp_id.strip()), "source": "fsp_results_table"}


class CombinedFspRegistry:
    """Сначала настоящая таблица, потом (если включено) демо-заглушка."""

    def __init__(self, primary: FspRegistryClient, fallback: FspRegistryClient | None):
        self.primary, self.fallback = primary, fallback

    def get_participant(self, fsp_id: str) -> dict | None:
        found = self.primary.get_participant(fsp_id)
        if found is None and self.fallback is not None:
            found = self.fallback.get_participant(fsp_id)
        return found


def build_registry() -> FspRegistryClient:
    return CombinedFspRegistry(FileFspRegistry(settings.fsp_data_path),
                               MockFspRegistry() if settings.fsp_demo_fallback else None)


PRIZE_POINTS = {1: 1.0, 2: 0.85, 3: 0.7}   # победитель и призёры
FINALIST_POINTS = 0.3
PARTICIPANT_POINTS = 0.15
NON_PRIZE_CAP = 0.6                         # участие без призов в сумме даёт не больше 0.6 очка


def compute_fsp_score(achievements: list[dict]) -> float:
    """
    Сила профиля ФСП (0..1) — по РЕЗУЛЬТАТИВНОСТИ и числу соревнований.

    По ответам организаторов: все соревнования и дисциплины равно важны (не считаем «чемпионат России
    выше хакатона»), а учитываем, победитель/призёр человек или просто участник, — и не даём набить
    профиль одними явками:
      - 1/2/3 место дают 1.0 / 0.85 / 0.7 очка за каждое соревнование;
      - финал без призового места — 0.3, участие — 0.15, но всё непризовое вместе — не больше 0.6 очка;
      - итог насыщается: 1 − e^(−очки/1.2). Одна победа ≈ 0.57, две призовых ≈ 0.79,
        сколько угодно участий без призов ≤ 0.39.
    Нет достижений -> 0 (кандидат НЕ исключается из выдачи, просто нет бонуса).
    Уровень соревнования хранится и показывается работодателю, но на балл не влияет.
    """
    prize = non_prize = 0.0
    for a in achievements or []:
        place = a.get("place")
        if place in PRIZE_POINTS:
            prize += PRIZE_POINTS[place]
        else:
            non_prize += FINALIST_POINTS if (a.get("result") or "").lower().startswith("финалист") else PARTICIPANT_POINTS
    points = prize + min(NON_PRIZE_CAP, non_prize)
    return round(1 - math.exp(-points / 1.2), 3)


registry: FspRegistryClient = build_registry()
