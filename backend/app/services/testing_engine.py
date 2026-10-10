"""
Движок тестирования — ЧИСТЫЕ функции (без базы данных).

Благодаря этому одну и ту же логику использует и API, и скрипт валидации
`scripts/evaluate.py`, который моделирует сотни кандидатов и считает метрики.

Механика:
  1. ПЛАН ТЕСТА (blueprint) одинаков для всех, кто идёт на один грейд:
     5 заданий уровня грейда, 3 — уровнем ниже, 2 — уровнем выше.
     -> сопоставимая сложность между кандидатами.
  2. Конкретные шаблоны выбираются случайно (seed попытки) из банка нужного уровня,
     а внутри шаблона — случайные параметры. -> у каждого свой вариант.
  3. Если тест строится под вакансию, шаблоны по навыкам вакансии выбираются чаще,
     но ПЛАН по уровням не меняется (сравнимость сохраняется).
  4. Балл взвешен по уровню задания: сложное задание весит больше.
"""
import random
from collections import defaultdict

from app.reference import GRADE_LEVEL
from app.services.code_runner import run_tests
from app.testing_bank import Template, templates_for

# Сколько заданий каждого «смещения уровня» берём (offset относительно уровня грейда)
BLUEPRINT = {0: 5, -1: 3, 1: 2}
MAX_LEVEL = 3


def item_weight(level: int) -> int:
    return level + 1


def plan_levels(target_level: int, total: int) -> list[int]:
    """Какие уровни заданий нужны. Если уровня нет (например, ниже Intern) — берём ближайший."""
    levels: list[int] = []
    for offset, count in BLUEPRINT.items():
        lvl = min(MAX_LEVEL, max(0, target_level + offset))
        levels += [lvl] * count
    if total < len(levels):  # тест короче — оставляем задания, ближайшие к уровню грейда
        levels = sorted(levels, key=lambda lv: abs(lv - target_level))[:total]
    elif total > len(levels):  # тест длиннее — добираем заданиями уровня грейда
        levels += [target_level] * (total - len(levels))
    return sorted(levels)


def build_items(spec: str, target_grade: str, seed: int, total: int = 10,
                prefer_skills: list[str] | None = None) -> list[dict]:
    """Собирает задания для попытки. Возвращает список заданий С ответами (хранится только на сервере)."""
    rng = random.Random(seed)
    target_level = GRADE_LEVEL[target_grade]
    pool = templates_for(spec)
    if not pool:
        raise ValueError(f"Нет заданий для специализации {spec}")
    prefer = {s.lower() for s in (prefer_skills or [])}
    chosen: list[Template] = []
    code_taken = False

    uses: dict[str, int] = {}
    for lvl in plan_levels(target_level, total):
        # Порядок выбора (важно для СОПОСТАВИМОЙ сложности):
        #  1) неиспользованный шаблон РОВНО этого уровня;
        #  2) повтор ПАРАМЕТРИЗОВАННОГО шаблона этого уровня (другие числа -> другой вопрос), не более 2 раз;
        #  3) только если банк уровня пуст — ближайший уровень (это сигнал, что банк надо пополнить).
        def ok(t: Template) -> bool:
            return not (t.kind == "code" and code_taken)
        candidates = [t for t in pool if t.level == lvl and t.id not in uses and ok(t)]
        if not candidates:
            candidates = [t for t in pool if t.level == lvl and t.parametric and t.kind != "code"
                          and uses.get(t.id, 0) < 2]
        if not candidates:
            for distance in range(1, MAX_LEVEL + 1):
                candidates = [t for t in pool if t.id not in uses and abs(t.level - lvl) == distance and ok(t)]
                if candidates:
                    break
        if not candidates:
            break  # банк исчерпан — тест будет короче (лучше, чем повторять вопросы)
        weights = [3.0 if t.skill.lower() in prefer else 1.0 for t in candidates]
        t = rng.choices(candidates, weights=weights, k=1)[0]
        uses[t.id] = uses.get(t.id, 0) + 1
        code_taken = code_taken or t.kind == "code"
        chosen.append(t)

    items = []
    texts: set[str] = set()
    for n, t in enumerate(sorted(chosen, key=lambda x: (x.level, x.kind == "code")), 1):
        for _ in range(8):  # при повторе шаблона следим, чтобы формулировки не совпали
            variant = t.make(random.Random(rng.getrandbits(32)))
            if variant["text"] not in texts:
                break
        texts.add(variant["text"])
        items.append({
            "id": f"q{n}", "template_id": t.id, "level": t.level, "skill": t.skill, "kind": t.kind,
            "weight": item_weight(t.level), "text": variant["text"], "options": variant.get("options"),
            "answer": variant.get("answer"), "code": variant.get("code"),
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
    total_w = got_w = 0.0
    by_skill: dict[str, list[float]] = defaultdict(list)
    by_level: dict[int, list[float]] = defaultdict(list)
    per_item = []
    for item in items:
        frac, details = grade_item(item, answers.get(item["id"]))
        total_w += item["weight"]
        got_w += item["weight"] * frac
        by_skill[item["skill"]].append(frac)
        by_level[item["level"]].append(frac)
        per_item.append({"id": item["id"], "template_id": item["template_id"], "skill": item["skill"],
                         "level": item["level"], "score": round(frac, 3), **details})
    score = round(100 * got_w / total_w, 1) if total_w else 0.0
    return {
        "score": score,
        "by_skill": {k: round(sum(v) / len(v), 3) for k, v in by_skill.items()},
        "by_level": {str(k): round(sum(v) / len(v), 3) for k, v in sorted(by_level.items())},
        "items": per_item,
    }


def public_item(item: dict) -> dict:
    """То, что видит фронтенд: БЕЗ правильного ответа и скрытых тестов."""
    out = {k: item[k] for k in ("id", "level", "skill", "kind", "text", "options")}
    if item.get("code"):
        c = item["code"]
        out["code"] = {"function_name": c["function_name"], "signature": c["signature"], "examples": c["examples"],
                       "language": "python", "starter_code": c["signature"] + "\n    pass\n"}
    else:
        out["code"] = None
    return out
