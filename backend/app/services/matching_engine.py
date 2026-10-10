"""
Движок подбора и ранжирования — ЧИСТЫЕ функции (без БД), чтобы их можно было
проверять скриптом валидации на синтетических парах «вакансия — кандидат».

Шаг 1. ФИЛЬТР по категории (специализация + грейд) — это делается в SQL. Категорию присваивает ТЕСТ;
        кандидат без теста попадает в выдачу по ЗАЯВЛЕННОЙ категории, с пометкой «не подтверждён»
        и множителем 0.6 — он виден, но всегда ниже подтверждённых с похожими данными.
Шаг 2. СКОРИНГ внутри категории — взвешенная сумма понятных компонент (каждая 0..1):

    test      — балл теста / 100                         «насколько подтверждён уровень»
    fsp       — сила достижений ФСП (0 если истории нет) «объективные соревнования»
    skills    — доля требуемых навыков, которые есть      «совпадение стека»
    text      — TF-IDF похожесть описания вакансии и резюме (простая NLP без внешних моделей)
    activity  — свежесть профиля + короткие задания       «актуальный сигнал»

    Итог = Σ w_i * x_i / Σ w_i  (компоненты без сигнала, например навыки не заданы, исключаются)
    Кандидат с грейдом на ступень ниже/выше нужного получает множитель 0.7 (на две ступени — 0.5).
    Грейд не подтверждён тестом — ещё множитель 0.6 (настройка RANK_UNVERIFIED_MULTIPLIER).

Шаг 3. ОБЪЯСНИМОСТЬ: для каждого кандидата формируем «плашки» — почему он в выдаче.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import settings
from app.ml import matching as ml_matching
from app.reference import GRADE_LEVEL, GRADE_NAME, category_label, fmt_score


@dataclass
class SearchCriteria:
    specialization: str | None = None
    grades: list[str] = field(default_factory=list)  # пусто = любые
    target_grade: str | None = None                  # «идеальный» грейд (из вакансии)
    skills: list[str] = field(default_factory=list)
    text: str | None = None                          # описание потребности/вакансии
    fsp_only: bool = False
    only_verified: bool = False
    min_test_score: float | None = None
    work_format: str | None = None
    city: str | None = None


@dataclass
class MatchResult:
    score: float                 # 0..100
    breakdown: dict              # вклад каждой компоненты
    reasons: list[dict]          # плашки для UI: {"type", "label", "positive"}
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)


# ----------------------------- мини-NLP ------------------------------------
_STOP = set("и в во не на с со по для от до из к ко у о об а но или что как это мы вы мы наш ваш "
            "the a an and or of to in on for with we you our is are be will опыт работы работа "
            "команда задачи требования знание умение".split())
_TOKEN = re.compile(r"[a-zа-яё0-9+#.]+", re.IGNORECASE)


def tokenize(text: str | None) -> list[str]:
    """Нижний регистр, без стоп-слов, грубый стемминг (обрезка до 6 букв для русских слов)."""
    out = []
    for raw in _TOKEN.findall((text or "").lower()):
        tok = raw.strip(".")
        if len(tok) < 2 or tok in _STOP:
            continue
        if re.match(r"[а-яё]", tok) and len(tok) > 6:
            tok = tok[:6]
        out.append(tok)
    return out


class TfIdf:
    """Классический TF-IDF по корпусу кандидатов. Строится на лету — для сотен профилей это миллисекунды."""

    def __init__(self, docs: list[list[str]]):
        n = len(docs) or 1
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def vec(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        v = {t: c * self.idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    @staticmethod
    def cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())


def candidate_document(c) -> list[str]:
    return tokenize(" ".join([c.about or "", " ".join(c.skills or []), c.resume_text or ""]))


# ----------------------------- компоненты -----------------------------------
def activity_score(c, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    last = c.last_activity_at or now
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - last).total_seconds() / 86400)
    fresh = 1.0 if days <= 14 else max(0.2, 1.0 - (days - 14) / 166 * 0.8)  # 14 дн -> 1.0, 180 дн -> 0.2
    tasks = (c.short_tasks_avg or 0) / 10 if c.short_tasks_done else 0.0
    return round(0.7 * fresh + 0.3 * tasks, 4)


def skills_overlap(required: list[str], have: list[str]) -> tuple[float, list[str], list[str]]:
    req = {s.lower(): s for s in required}
    got = {s.lower() for s in (have or [])}
    matched = [req[k] for k in req if k in got]
    missing = [req[k] for k in req if k not in got]
    return (len(matched) / len(req) if req else 0.0), matched, missing


def _days_ago(dt: datetime | None) -> int | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int((datetime.now(timezone.utc) - dt).total_seconds() // 86400)


def _fsp_label(c) -> tuple[str, bool]:
    ach = c.fsp_achievements or []
    rank = getattr(c, "fsp_rank", None)
    rank_txt = f" · {rank}" if rank else ""
    if not c.fsp_id:
        return "Нет истории ФСП — оценка по тесту", False
    if not ach:
        return f"ФСП ID {c.fsp_id}: участник, соревнований пока нет{rank_txt}", False
    places = [a.get("place") for a in ach if isinstance(a.get("place"), int) and a.get("place") <= 3]
    if places:
        res = f"призёр {len(places)} из {len(ach)} соревн., лучшее — {min(places)} место"
    else:
        res = f"{len(ach)} соревн. без призовых мест"
    return f"ФСП ID {c.fsp_id}: {res}{rank_txt}", True


# ----------------------------- главный расчёт --------------------------------
def score_candidate(c, crit: SearchCriteria, tfidf: TfIdf | None = None, query_vec: dict | None = None) -> MatchResult:
    w = {"test": settings.rank_w_test, "fsp": settings.rank_w_fsp, "skills": settings.rank_w_skills,
         "text": settings.rank_w_text, "activity": settings.rank_w_activity}
    verified = bool(c.grade and c.specialization)
    spec, grade = ((c.specialization, c.grade) if verified
                   else (getattr(c, "declared_specialization", None), getattr(c, "declared_grade", None)))
    x: dict[str, float] = {
        "test": (c.test_score or 0) / 100 if verified else 0.0,
        "fsp": c.fsp_score or 0.0,
        "activity": activity_score(c),
    }
    reasons: list[dict] = []
    matched: list[str] = []
    missing: list[str] = []

    # 1) Категория и тест
    cat = category_label(spec, grade)
    if verified:
        reasons.append({"type": "test", "positive": (c.test_score or 0) >= 70,
                        "label": f"{cat}: тест {fmt_score(c.test_score or 0)}/100"})
    else:
        reasons.append({"type": "test", "positive": False,
                        "label": f"{cat}: грейд заявлен кандидатом, тест ещё не пройден"})

    # 2) Навыки
    if crit.skills:
        frac, matched, missing = skills_overlap(crit.skills, c.skills)
        x["skills"] = frac
        label = f"Стек совпадает {len(matched)} из {len(crit.skills)}"
        if matched:
            label += ": " + ", ".join(matched[:5])
        reasons.append({"type": "skills", "positive": frac >= 0.5, "label": label, "missing": missing})
    else:
        w.pop("skills")

    # 3) Текстовая релевантность: ML-похожесть (app/ml/matching.py), если подключена, иначе TF-IDF
    if crit.text and crit.text.strip() and ml_matching.ENABLED:
        try:
            sim = float(ml_matching.text_similarity(crit.text + " " + " ".join(crit.skills),
                                                    " ".join([c.about or "", " ".join(c.skills or []),
                                                              c.resume_text or ""])))
            x["text"] = min(1.0, max(0.0, sim))
        except Exception:
            w.pop("text")
        else:
            if x["text"] >= 0.5:
                reasons.append({"type": "text", "positive": True, "label": "Опыт похож на задачи из описания"})
    elif tfidf is not None and query_vec:
        doc_vec = tfidf.vec(candidate_document(c))
        sim = TfIdf.cosine(query_vec, doc_vec)
        x["text"] = min(1.0, sim * 2.5)  # косинус редко > 0.4, растягиваем шкалу
        common = sorted((t for t in query_vec if t in doc_vec), key=lambda t: -query_vec[t] * doc_vec[t])[:3]
        if common and x["text"] >= 0.25:
            reasons.append({"type": "text", "positive": True,
                            "label": "Опыт перекликается с описанием: " + ", ".join(common)})
    else:
        w.pop("text")

    # 4) ФСП
    fsp_label, fsp_pos = _fsp_label(c)
    reasons.append({"type": "fsp", "positive": fsp_pos, "label": fsp_label})

    # 5) Сильные темы теста
    strong = [k for k, v in (c.skill_scores or {}).items() if v >= 0.8]
    if strong:
        reasons.append({"type": "strengths", "positive": True, "label": "Сильные темы теста: " + ", ".join(strong[:3])})

    # 6) Активность
    days = _days_ago(c.last_activity_at)
    act = f"Активен {days} дн. назад" if days is not None else "Активность неизвестна"
    if c.short_tasks_done:
        act += f" · коротких заданий: {c.short_tasks_done} (ср. {c.short_tasks_avg or 0:.1f}/10)"
    reasons.append({"type": "activity", "positive": x["activity"] >= 0.7, "label": act})

    total_w = sum(w.values())
    raw = sum(w[k] * x[k] for k in w) / total_w

    # 7) Соответствие грейда
    mult = 1.0
    if crit.target_grade and grade and grade != crit.target_grade:
        diff = abs(GRADE_LEVEL[grade] - GRADE_LEVEL[crit.target_grade])
        mult = settings.rank_adjacent_grade_multiplier if diff == 1 else 0.5
        reasons.append({"type": "grade", "positive": False,
                        "label": f"Грейд {GRADE_NAME[grade]} вместо {GRADE_NAME[crit.target_grade]}"})
    # 8) Неподтверждённый грейд: виден, но ниже (ответы организаторов: «показывать со статусом и опускать»)
    if not verified:
        mult *= settings.rank_unverified_multiplier

    score = round(100 * raw * mult, 1)
    breakdown = {k: {"value": round(x[k], 3), "weight": round(w[k] / total_w, 3),
                     "contribution": round(100 * w[k] * x[k] / total_w * mult, 1)} for k in w}
    breakdown["grade_multiplier"] = round(mult, 3)
    return MatchResult(score=score, breakdown=breakdown, reasons=reasons, matched_skills=matched, missing_skills=missing)


def passes_filters(c, crit: SearchCriteria) -> bool:
    """Фильтры, которые не удобно делать в SQL (JSON-поля). Категорийный фильтр — в SQL."""
    if crit.fsp_only and not (c.fsp_achievements or []):
        return False
    if crit.only_verified and not (c.grade and c.specialization):
        return False
    if crit.min_test_score is not None and (c.test_score or 0) < crit.min_test_score:
        return False
    if crit.work_format and c.work_format and c.work_format != crit.work_format and c.work_format != "hybrid":
        return False
    if crit.city and crit.work_format != "remote" and c.city and c.city.lower() != crit.city.lower():
        return False
    return True


def rank(candidates: list, crit: SearchCriteria) -> list[tuple[object, MatchResult]]:
    """Ранжирует список кандидатов. Возвращает [(кандидат, результат)] по убыванию балла."""
    pool = [c for c in candidates if passes_filters(c, crit)]
    tfidf = query_vec = None
    if crit.text and crit.text.strip():
        docs = [candidate_document(c) for c in pool]
        tfidf = TfIdf(docs)
        query_vec = tfidf.vec(tokenize(crit.text + " " + " ".join(crit.skills)))
    scored = [(c, score_candidate(c, crit, tfidf, query_vec)) for c in pool]
    scored.sort(key=lambda p: (-p[1].score, -(p[0].test_score or 0), p[0].id or 0))
    return scored
