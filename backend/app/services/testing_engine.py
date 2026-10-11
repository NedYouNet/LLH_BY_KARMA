"""
Движок тестирования — ЧИСТЫЕ функции (без базы данных).

Благодаря этому одну и ту же логику использует и API, и скрипт валидации
`scripts/evaluate.py`, который моделирует сотни кандидатов и считает метрики.

Механика:
  Новый размеченный банк: лёгкая, средняя, сложная задача целевого грейда.
  Баллы: 15+5, 20+10, 35+15. Бонус только за все скрытые тесты.
  Сохранённые старые попытки проверяются по их сохранённым весам.
  Все пять направлений используют банк ML с разметкой easy/mid/hard.
"""
import random
import copy
import re
from collections import defaultdict

from app.reference import GRADE_LEVEL
from app.services.code_runner import run_tests
from app.testing_bank import templates_for

# Грейд (level) и сложность задачи — независимые оси.
CONTEST_WEIGHTS = (
    {"base": 15, "bonus": 5},
    {"base": 20, "bonus": 10},
    {"base": 35, "bonus": 15},
)
DIFFICULTIES = ("easy", "medium", "hard")


def template_difficulty(template) -> str | None:
    match = re.search(r"\.code\.([0-3])_(easy|mid|medium|hard)_", template.id)
    if not match or int(match[1]) != template.level or template.kind != "code":
        return None
    return "medium" if match[2] == "mid" else match[2]


def plan_levels(target_level: int, total: int = 3) -> list[int]:
    """Совместимость импортов: три задачи строго выбранного грейда."""
    return [target_level] * 3


def build_items(spec: str, target_grade: str, seed: int, total: int = 3,
                prefer_skills: list[str] | None = None) -> list[dict]:
    """Одна лёгкая, средняя и сложная задача целевого грейда, именно в этом порядке."""
    rng = random.Random(seed)
    level = GRADE_LEVEL[target_grade]
    pool = [t for t in templates_for(spec) if t.level == level and template_difficulty(t)]
    prefer = {s.lower() for s in (prefer_skills or [])}
    items = []
    for index, difficulty in enumerate(DIFFICULTIES):
        candidates = [t for t in pool if template_difficulty(t) == difficulty]
        if not candidates:
            raise ValueError(f"Банк {spec}/{target_grade}: отсутствует задача {difficulty}")
        template = rng.choices(candidates, weights=[3 if t.skill.lower() in prefer else 1 for t in candidates])[0]
        variant = copy.deepcopy(template.make(random.Random(rng.getrandbits(64))))
        # Показываем пример именно с данными сгенерированного варианта.
        # Фиксированная легенда не обязана меняться между попытками.
        if variant["code"].get("tests"):
            variant["code"]["examples"] = [copy.deepcopy(variant["code"]["tests"][0])]
        weights = CONTEST_WEIGHTS[index]
        items.append({
            "id": f"q{index + 1}", "template_id": template.id, "level": level,
            "difficulty": difficulty, "kind": "code", "skill": template.skill,
            "base_weight": weights["base"], "bonus_weight": weights["bonus"],
            "weight": weights["base"] + weights["bonus"], "text": variant["text"],
            "options": variant.get("options"), "answer": variant.get("answer"), "code": variant["code"],
        })
    return items


def _normalize(value) -> str:
    return str(value).strip().lower().replace(",", ".").strip('"').strip("'")


def grade_item(item: dict, answer) -> tuple[float, dict]:
    """Оценивает один ответ. Возвращает (доля верности 0..1, детали)."""
    if answer is None or answer == "":
        return 0.0, {"status": "no_answer"}
    kind = item["kind"]
    if kind == "single":
        ok = str(answer) == str(item["answer"])
        return float(ok), {"status": "correct" if ok else "wrong"}
    if kind == "input":
        a, b = _normalize(answer), _normalize(item["answer"])
        try:
            ok = abs(float(a) - float(b)) < 0.011
        except ValueError:
            ok = a == b
        return float(ok), {"status": "correct" if ok else "wrong"}
    if kind == "code":
        res = run_tests(str(answer), item["code"]["function_name"], item["code"]["tests"])
        frac = res["passed"] / res["total"] if res["total"] else 0.0
        return frac, {"status": "correct" if frac == 1 else ("partial" if frac > 0 else "wrong"),
                      "passed": res["passed"], "total": res["total"],
                      "violations": res.get("violations", []), "errors": res.get("errors", [])}
    return 0.0, {"status": "unknown_kind"}


def score_attempt(items: list[dict], answers: dict) -> dict:
    """
    Итог попытки: общий балл (0..100), разбор по навыкам и уровням.
    answers: {"q1": "201", "q2": "...", ...}
    """
    contest = any("base_weight" in i or "bonus_weight" in i for i in items)
    if contest and (len(items) != 3 or any(
        i.get("base_weight") != CONTEST_WEIGHTS[n]["base"] or
        i.get("bonus_weight") != CONTEST_WEIGHTS[n]["bonus"]
        for n, i in enumerate(items)
    )):
        raise ValueError("Повреждена матрица баллов контеста")
    total_w = got_w = 0.0
    total_points = 0.0
    by_skill: dict[str, list[float]] = defaultdict(list)
    by_level: dict[int, list[float]] = defaultdict(list)
    per_item = []
    for item in items:
        frac, details = grade_item(item, answers.get(item["id"]))
        points = item["base_weight"] * frac + (item["bonus_weight"] if frac == 1.0 else 0) if contest else None
        if contest:
            total_points += points
        total_w += item["weight"]
        got_w += item["weight"] * frac
        by_skill[item["skill"]].append(frac)
        by_level[item["level"]].append(frac)
        per_item.append({"id": item["id"], "template_id": item["template_id"], "skill": item["skill"],
                         "level": item["level"], "score": round(points, 2) if contest else round(frac, 3),
                         "fraction": frac, "difficulty": item.get("difficulty"),
                         **({"base_weight": item["base_weight"], "bonus_weight": item["bonus_weight"],
                             "max_score": item["base_weight"] + item["bonus_weight"]} if contest else {}), **details})
    score = round(total_points, 1) if contest else (round(100 * got_w / total_w, 1) if total_w else 0.0)
    return {
        "score": score,
        "by_skill": {k: round(sum(v) / len(v), 3) for k, v in by_skill.items()},
        "by_level": {str(k): round(sum(v) / len(v), 3) for k, v in sorted(by_level.items())},
        "items": per_item,
    }


def public_item(item: dict) -> dict:
    """То, что видит фронтенд: БЕЗ правильного ответа и скрытых тестов."""
    out = {k: item[k] for k in ("id", "level", "skill", "kind", "text", "options")}
    out["difficulty"] = item.get("difficulty")
    if "base_weight" in item:
        out.update(base_weight=item["base_weight"], bonus_weight=item["bonus_weight"],
                   max_score=item["base_weight"] + item["bonus_weight"])
    if item.get("code"):
        c = item["code"]
        out["code"] = {"function_name": c["function_name"], "signature": c["signature"], "examples": c["examples"],
                       "language": "python", "starter_code": c["signature"] + "\n    pass\n",
                       "checks_used": item.get("checks_used", 0), "check_limit": 10}
    else:
        out["code"] = None
    return out
