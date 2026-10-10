"""
Собственная процедура валидации решения (ТЗ, раздел 3.4 и критерий оценки №2).

Эталонной разметки в хакатоне нет, поэтому строим СИНТЕТИЧЕСКУЮ популяцию, у которой
мы знаем «истинный» уровень каждого кандидата (это и есть наша эталонная разметка),
и прогоняем через НАСТОЯЩИЙ код продукта (банк заданий, движок тестирования, ранжирование).

Часть A. Механика тестирования
  Модель ответа — IRT 2PL: P(верно) = 1 / (1 + e^(-a·(θ − b))), где θ — истинный уровень кандидата,
  b = уровень задания − 0.75, a = 1.7. Истинный грейд = floor(θ): θ∈[1,2) — Junior и т.д.
  Кандидат идёт по правилам продукта: заявляет грейд (ошибается на ±1 в 40% случаев), проходит тест,
  не прошёл — пробует ниже, прошёл на 90%+ — пробует выше.
  Метрики: 1) точность категоризации против эталона; 2) согласованность (повторное прохождение
  с другими вариантами даёт тот же грейд?); 3) дискриминативность заданий; 4) устойчивость к утечке.

Часть B. Механика подбора
  Резюме «врёт»: кандидат дописывает 0–4 навыка, которых не знает. Тест отражает истинный уровень.
  Релевантный кандидат = нужная специализация, истинный грейд = грейд вакансии и истинный стек
  покрывает ≥ 60% навыков вакансии. Сравниваем наш ранкер с «классическим джоб-сайтом»
  (сортировка по совпадению ключевых слов резюме) и с ранжированием только по баллу теста.
  Метрики: Precision@10 и nDCG@10.

Запуск:  python -m scripts.evaluate            (результаты: scripts/output/evaluation.json и .md)
"""
import json
import math
import random
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.reference import GRADE_CODES, SKILLS
from app.services.matching_engine import SearchCriteria, rank
from app.services.testing_engine import build_items
ML_TASKS_PER_ATTEMPT = 3

A, B_SHIFT, PASS, UPGRADE = 1.7, 0.75, 70.0, 90.0
OUT = Path(__file__).parent / "output"
rnd = random.Random(42)


# ============================ ЧАСТЬ A ============================
def p_correct(theta: float, level: int) -> float:
    return 1 / (1 + math.exp(-A * (theta - (level - B_SHIFT))))


def take_test(theta: float, spec: str, grade: str, seed: int, r: random.Random, total: int = 10) -> tuple[float, list]:
    items = build_items(spec, grade, seed, total)
    got = total = 0.0
    log = []
    for it in items:
        ok = r.random() < p_correct(theta, it["level"])
        got += ((it["base_weight"] + it["bonus_weight"]) * ok if "base_weight" in it else it["weight"] * ok)
        total += it["weight"]
        log.append((it["template_id"], ok))
    return 100 * got / total, log


def run_path(theta: float, spec: str, r: random.Random, total: int = 10) -> tuple[str | None, float | None]:
    """Путь кандидата по правилам продукта. Возвращает (грейд, балл)."""
    true_g = min(3, max(0, int(theta)))
    declared = min(3, max(0, true_g + r.choice([-1, 0, 0, 0, 1])))
    g, result, res_score, tried_up = declared, None, None, False
    while True:
        score, _ = take_test(theta, spec, GRADE_CODES[g], r.randrange(10**9), r, total)
        if score >= PASS:
            result, res_score = g, score
            if score >= UPGRADE and g < 3 and not tried_up:
                tried_up, g = True, g + 1
                continue
            return GRADE_CODES[result], res_score
        if result is not None:  # провалил попытку повышения — грейд сохраняется
            return GRADE_CODES[result], res_score
        if g == 0 or tried_up:
            return None, None
        g -= 1


def part_a(n: int = 400, spec: str = "backend", total: int = 10, full: bool = True) -> dict:
    # Все направления имеют фиксированные 3 задачи; это синтетическая модель,
    # а не измерение точности на реальных кандидатах или проверка решений.
    total = ML_TASKS_PER_ATTEMPT
    r = random.Random(1)
    thetas = [r.uniform(0.0, 3.999) for _ in range(n)]
    first, second = [], []
    for th in thetas:
        first.append(run_path(th, spec, r, total))
        second.append(run_path(th, spec, r, total))
    truth = [GRADE_CODES[int(th)] for th in thetas]
    lvl = {g: i for i, g in enumerate(GRADE_CODES)}

    def acc(res, exact=True):
        ok = [(g is not None and (g == t if exact else abs(lvl[g] - lvl[t]) <= 1)) for (g, _), t in zip(res, truth)]
        return sum(ok) / len(ok)

    agree = sum(1 for (g1, _), (g2, _) in zip(first, second) if g1 == g2) / n
    agree1 = sum(1 for (g1, _), (g2, _) in zip(first, second)
                 if g1 == g2 or (g1 and g2 and abs(lvl[g1] - lvl[g2]) <= 1)) / n
    # «Уверенные» случаи: истинный уровень не у самой границы грейдов (|θ − граница| > 0.25)
    far = [i for i, th in enumerate(thetas) if 0.25 < th - int(th) < 0.75]
    acc_far = sum(1 for i in far if first[i][0] == truth[i]) / len(far)
    if not full:
        return {"test_length": total, "accuracy_exact": round(acc(first), 3), "test_retest_agreement": round(agree, 3)}

    # Дискриминативность: тест на Middle для всей популяции, корреляция «задание верно» с баллом за остальное
    per_tpl: dict[str, list[tuple[int, float]]] = {}
    scores_by_true: dict[str, list[float]] = {g: [] for g in GRADE_CODES}
    for th in thetas:
        score, log = take_test(th, spec, "middle", r.randrange(10**9), r)
        scores_by_true[GRADE_CODES[int(th)]].append(score)
        for tpl, ok in log:
            per_tpl.setdefault(tpl, []).append((int(ok), score))
    rpbs = []
    for vals in per_tpl.values():
        xs, ys = [v[0] for v in vals], [v[1] for v in vals]
        if len(set(xs)) > 1 and len(vals) > 20:
            rpbs.append(statistics.correlation(xs, ys))

    # Утечка: «шпаргалка» с чужого варианта — сколько ответов совпадёт с моим вариантом
    overlaps = []
    for _ in range(300):
        g = r.choice(GRADE_CODES)
        a, b = build_items(spec, g, r.randrange(10**9)), build_items(spec, g, r.randrange(10**9))
        key = {(i["template_id"], json.dumps(i["answer"] if i["kind"] != "code" else i["code"]["tests"], ensure_ascii=False))
               for i in a}
        w_total = sum(i["weight"] for i in b)
        w_leak = sum(i["weight"] for i in b if (i["template_id"], json.dumps(
            i["answer"] if i["kind"] != "code" else i["code"]["tests"], ensure_ascii=False)) in key)
        overlaps.append(100 * w_leak / w_total)

    return {
        "test_length": total,
        "population": n,
        "accuracy_exact": round(acc(first), 3),
        "accuracy_within_1": round(acc(first, exact=False), 3),
        "accuracy_exact_far_from_boundary": round(acc_far, 3),
        "test_retest_agreement": round(agree, 3),
        "test_retest_agreement_within_1": round(agree1, 3),
        "no_grade_share": round(sum(1 for g, _ in first if g is None) / n, 3),
        "item_discrimination_mean_rpb": round(statistics.mean(rpbs), 3),
        "item_discrimination_min_rpb": round(min(rpbs), 3),
        "middle_test_score_by_true_grade": {g: round(statistics.mean(v), 1) for g, v in scores_by_true.items() if v},
        "leak_score_from_foreign_key_mean": round(statistics.mean(overlaps), 1),
        "leak_score_fixed_test_baseline": 100.0,
    }


# ============================ ЧАСТЬ B ============================
def make_population(n: int, r: random.Random) -> list[SimpleNamespace]:
    now = datetime.now(timezone.utc)
    people = []
    for i in range(n):
        spec = r.choice(list(SKILLS))
        core = SKILLS[spec][:12]
        theta = r.uniform(0, 3.999)
        stack = r.sample(core, r.randint(3, 6))
        fake_skills = r.sample([s for s in core if s not in stack], r.randint(0, 4))  # приписанные навыки
        grade, score = run_path(theta, spec, r)
        has_fsp = r.random() < 0.15 + 0.12 * theta
        fsp = min(1.0, max(0.05, 0.22 * theta + r.gauss(0, 0.15))) if has_fsp else 0.0
        resume_skills = stack + fake_skills
        people.append(SimpleNamespace(
            id=i, spec_declared=spec, specialization=spec if grade else None, grade=grade, test_score=score,
            true_grade=GRADE_CODES[int(theta)], true_stack=set(stack), skills=resume_skills,
            fsp_id=str(100001 + i) if has_fsp else None, fsp_score=fsp,
            fsp_achievements=[{"place": 2}] if has_fsp else [], about=" ".join(resume_skills), resume_text="",
            skill_scores={}, last_activity_at=now - timedelta(days=r.randint(0, 120)), short_tasks_done=0,
            short_tasks_avg=None, work_format=None, city=None, experience_years=theta * 1.5,
        ))
    return people


def precision_ndcg(ranked_ids: list[int], relevant: set[int], k: int = 10) -> tuple[float, float]:
    top = ranked_ids[:k]
    hits = [1 if i in relevant else 0 for i in top]
    dcg = sum(h / math.log2(n + 2) for n, h in enumerate(hits))
    idcg = sum(1 / math.log2(n + 2) for n in range(min(k, len(relevant))))
    return sum(hits) / k, (dcg / idcg if idcg else 0.0)


def part_b(n_candidates: int = 900, n_vacancies: int = 40) -> dict:
    r = random.Random(7)
    people = make_population(n_candidates, r)
    lvl = {g: i for i, g in enumerate(GRADE_CODES)}
    res = {"ours": [], "keywords_baseline": [], "test_only": []}
    cat_prec = {k: [] for k in res}
    used = 0
    for _ in range(n_vacancies * 3):
        if used >= n_vacancies:
            break
        spec = r.choice(list(SKILLS))
        grade = r.choice(GRADE_CODES)
        vskills = r.sample(SKILLS[spec][:12], r.randint(3, 5))
        relevant = {p.id for p in people if p.spec_declared == spec and p.true_grade == grade
                    and len(p.true_stack & set(vskills)) / len(vskills) >= 0.6}
        if len(relevant) < 3:
            continue
        used += 1
        # 1) наш ранкер: только прошедшие тест, категория + соседние грейды
        grades = [g for g in GRADE_CODES if abs(lvl[g] - lvl[grade]) <= 1]
        pool = [p for p in people if p.specialization == spec and p.grade in grades]
        crit = SearchCriteria(specialization=spec, grades=grades, target_grade=grade, skills=vskills,
                              text=" ".join(vskills))
        ours = [p.id for p, _ in rank(pool, crit)]
        # 2) «классический джоб-сайт»: все с этой специализацией, сортировка по совпадению ключевых слов резюме
        kw = sorted([p for p in people if p.spec_declared == spec],
                    key=lambda p: (-len(set(p.skills) & set(vskills)), -p.experience_years))
        # 3) только балл теста внутри категории
        to = sorted([p for p in pool if p.grade == grade], key=lambda p: -(p.test_score or 0))
        by_id = {p.id: p for p in people}
        for name, ids in (("ours", ours), ("keywords_baseline", [p.id for p in kw]), ("test_only", [p.id for p in to])):
            res[name].append(precision_ndcg(ids, relevant))
            top = ids[:10]
            cat_prec[name].append(sum(by_id[i].true_grade == grade for i in top) / max(1, len(top)))
    return {name: {"precision_at_10": round(statistics.mean(v[0] for v in vals), 3),
                   "ndcg_at_10": round(statistics.mean(v[1] for v in vals), 3),
                   "true_grade_share_in_top10": round(statistics.mean(cat_prec[name]), 3)}
            for name, vals in res.items()} | {
        "vacancies_evaluated": used, "candidates": n_candidates}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    print("Часть A: тестирование...")
    a = part_a()
    print(json.dumps(a, ensure_ascii=False, indent=2))
    print("Эксперимент: длина теста...")
    a["length_experiment"] = [part_a(total=ML_TASKS_PER_ATTEMPT, full=False)]
    print(json.dumps(a["length_experiment"], ensure_ascii=False))
    print("Часть B: подбор...")
    b = part_b()
    print(json.dumps(b, ensure_ascii=False, indent=2))
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "testing": a, "matching": b,
              "assumptions": {"irt_a": A, "irt_b_shift": B_SHIFT, "pass_threshold": PASS, "upgrade_threshold": UPGRADE}}
    (OUT / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# Результаты валидации", "", "## Тестирование", "| Метрика | Значение |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in a.items() if k != "length_experiment"]
    md += ["", "## Длина теста", "| Заданий | Точность | Согласованность |", "|---|---|---|"]
    md += [f"| {x['test_length']} | {x['accuracy_exact']} | {x['test_retest_agreement']} |" for x in a["length_experiment"]]
    md += ["", "## Подбор", "| Ранкер | P@10 | nDCG@10 | Доля верного грейда в топ-10 |", "|---|---|---|---|"]
    md += [f"| {k} | {v['precision_at_10']} | {v['ndcg_at_10']} | {v['true_grade_share_in_top10']} |"
           for k, v in b.items() if isinstance(v, dict)]
    (OUT / "evaluation.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Отчёт: {OUT / 'evaluation.md'}")


if __name__ == "__main__":
    main()
