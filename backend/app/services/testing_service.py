"""
Тестирование и присвоение категории.

ПРАВИЛА (их стоит проговорить на защите):
 1. Сначала опрос (специализация, стек, заявленный грейд), потом тест.
 2. Категория (специализация + грейд) присваивается ТОЛЬКО по итогам теста.
 3. Порог прохождения — 70% (взвешенно по сложности заданий).
 4. Грейд НЕ понижается принудительно: провал теста на уровень выше ничего не отнимает.
 5. Не прошёл на заявленный уровень — можно сразу пройти тест на уровень ниже.
 6. Смена грейда — не чаще раза в 90 дней.
    Исключение: кто сдал свой уровень на 90%+, может сразу попробовать следующий («уверенно справился»).
 7. Пересдача на тот же уровень — не чаще раза в 24 часа (защита от перебора банка заданий).
 8. Одна активная попытка; ответы после дедлайна (+1 мин на сеть) не засчитываются.
"""
import secrets
from datetime import timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import BadRequest, Conflict, NotFound
from app.models import CandidateProfile, GradeHistory, TestAttempt, Vacancy
from app.reference import GRADE_CODES, GRADE_LEVEL, GRADE_NAME, category_label
from app.repositories.repos import AttemptRepository, CandidateRepository
from app.schemas.candidate import CategoryStatus, GradeHistoryOut, GradeTarget
from app.schemas.testing import AttemptOut, AttemptResultOut, AttemptSummary, GradeDecision
from app.services.testing_engine import build_items, public_item, score_attempt

GRACE = timedelta(minutes=1)


def _aware(dt):
    """SQLite в тестах теряет часовой пояс — возвращаем его (в PostgreSQL он и так есть)."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class TestingService:
    __test__ = False

    def __init__(self, db: Session):
        self.db = db
        self.attempts = AttemptRepository(db)

    # ------------------------------------------------------------------ правила
    def next_change_at(self, c: CandidateProfile):
        if not c.grade:
            return None
        base = _aware(c.grade_changed_at or c.grade_assigned_at)
        return base + timedelta(days=settings.grade_change_cooldown_days) if base else None

    def _confident_upgrade(self, c: CandidateProfile, target: str) -> bool:
        """Правило 6: сдал свой грейд на 90%+ после последней смены -> можно сразу на ступень выше."""
        if not c.grade or GRADE_LEVEL[target] != GRADE_LEVEL[c.grade] + 1:
            return False
        last = self.attempts.last_for_target(c.id, c.specialization, c.grade)
        return bool(last and last.status == "completed" and (last.score or 0) >= settings.test_upgrade_hint_threshold)

    def check_can_start(self, c: CandidateProfile, spec: str, target: str) -> tuple[bool, str | None, str | None]:
        """Возвращает (можно?, код ошибки, сообщение)."""
        if not c.survey:
            return False, "SURVEY_REQUIRED", "Сначала пройдите опрос по отрасли и специализации"
        now = utcnow()
        is_change = c.grade is not None and (target != c.grade or spec != c.specialization)
        nca = self.next_change_at(c)
        if is_change and nca and nca > now and not self._confident_upgrade(c, target):
            return False, "GRADE_COOLDOWN", f"Сменить грейд можно после {nca:%d.%m.%Y}"
        last = self.attempts.last_for_target(c.id, spec, target)
        if last and last.status != "in_progress":
            retry_at = _aware(last.started_at) + timedelta(hours=settings.test_retry_cooldown_hours)
            if retry_at > now:
                return False, "RETRY_COOLDOWN", f"Повторно пройти тест на этот уровень можно после {retry_at:%d.%m.%Y %H:%M} UTC"
        return True, None, None

    # ---------------------------------------------------------------- попытки
    def _expire_if_needed(self, a: TestAttempt) -> None:
        if a.status == "in_progress" and utcnow() > _aware(a.deadline_at) + GRACE:
            a.status = "expired"
            a.finished_at = utcnow()
            a.passed = False
            self.db.commit()

    def start(self, c: CandidateProfile, spec: str, target: str, vacancy_id: int | None) -> AttemptOut:
        active = self.attempts.active(c.id)
        if active:
            self._expire_if_needed(active)
            if active.status == "in_progress":
                raise Conflict("У вас уже есть незавершённый тест", "ATTEMPT_IN_PROGRESS", {"attempt_id": active.id})
        ok, code, msg = self.check_can_start(c, spec, target)
        if not ok:
            raise Conflict(msg, code, {"next_change_at": str(self.next_change_at(c))} if code == "GRADE_COOLDOWN" else None)
        prefer = None
        if vacancy_id:
            v = self.db.get(Vacancy, vacancy_id)
            if not v:
                raise NotFound("Вакансия не найдена")
            prefer = v.skills
        seed = secrets.randbits(31)
        items = build_items(spec, target, seed, settings.test_questions_count, prefer)
        now = utcnow()
        a = self.attempts.add(TestAttempt(candidate_id=c.id, specialization=spec, target_grade=target, seed=seed,
                                          vacancy_id=vacancy_id, items=items, answers={}, started_at=now,
                                          deadline_at=now + timedelta(minutes=settings.test_duration_minutes)))
        c.last_activity_at = now
        self.db.commit()
        return self.attempt_out(a)

    def get_owned(self, c: CandidateProfile, attempt_id: int) -> TestAttempt:
        a = self.attempts.get(attempt_id)
        if not a or a.candidate_id != c.id:  # чужие попытки «не существуют»
            raise NotFound("Попытка не найдена")
        self._expire_if_needed(a)
        return a

    @staticmethod
    def attempt_out(a: TestAttempt) -> AttemptOut:
        left = int((_aware(a.deadline_at) - utcnow()).total_seconds())
        return AttemptOut(id=a.id, specialization=a.specialization, target_grade=a.target_grade, status=a.status,
                          started_at=a.started_at, deadline_at=a.deadline_at, seconds_left=max(0, left),
                          items=[public_item(i) for i in a.items], score=a.score, passed=a.passed,
                          finished_at=a.finished_at)

    def submit(self, c: CandidateProfile, attempt_id: int, answers: dict[str, str]) -> AttemptResultOut:
        a = self.get_owned(c, attempt_id)
        if a.status == "completed":
            raise Conflict("Тест уже завершён", "ATTEMPT_FINISHED")
        valid_ids = {i["id"] for i in a.items}
        unknown = set(answers) - valid_ids
        if unknown:
            raise BadRequest(f"Неизвестные задания: {sorted(unknown)}", "UNKNOWN_ITEMS")

        expired = a.status == "expired"
        result = score_attempt(a.items, answers)
        score = result["score"]
        passed = (not expired) and score >= settings.test_pass_threshold
        now = utcnow()
        a.answers, a.score, a.passed, a.finished_at = answers, score, passed, now
        a.status = "expired" if expired else "completed"

        for it in result["items"]:  # калибровка банка
            self.attempts.bump_stat(it["template_id"], it["score"], score)

        decision = self._decide(c, a, score, passed, expired, result["by_skill"])
        a.result = {**result, "decision": decision.model_dump(mode="json")}
        c.last_activity_at = now
        self.db.commit()
        return self.result_out(a)

    def _decide(self, c: CandidateProfile, a: TestAttempt, score: float, passed: bool, expired: bool,
                by_skill: dict) -> GradeDecision:
        before = c.grade
        spec, target = a.specialization, a.target_grade
        now = utcnow()
        upgrade = passed and score >= settings.test_upgrade_hint_threshold and GRADE_LEVEL[target] < 3

        if expired:
            return GradeDecision(grade_before=before, grade_after=before, changed=False,
                                 message="Время вышло — попытка не засчитана", next_change_at=self.next_change_at(c))
        if not passed:
            if before is None:
                lower = GRADE_CODES[GRADE_LEVEL[target] - 1] if GRADE_LEVEL[target] > 0 else None
                msg = (f"Порог {settings.test_pass_threshold:.0f}% не набран. Можно сразу пройти тест на уровень "
                       f"{GRADE_NAME[lower]}" if lower else "Порог не набран. Попробуйте снова через 24 часа")
            else:
                msg = f"Порог не набран. Ваш грейд {GRADE_NAME[before]} сохранён — он не понижается"
            return GradeDecision(grade_before=before, grade_after=before, changed=False, message=msg,
                                 next_change_at=self.next_change_at(c))

        changed = before != target or c.specialization != spec
        c.test_score = score
        c.skill_scores = by_skill
        if changed:
            self.db.add(GradeHistory(candidate_id=c.id, specialization=spec, old_grade=before, new_grade=target,
                                     attempt_id=a.id, reason=f"Тест {score:.0f}/100"))
            if before is None:
                c.grade_assigned_at = now
            c.grade_changed_at = now
            c.specialization, c.grade = spec, target
            msg = f"Поздравляем! Ваша категория: {category_label(spec, target)}"
        else:
            msg = f"Грейд {GRADE_NAME[target]} подтверждён, балл обновлён"
        if upgrade:
            msg += f". Вы уверенно справились — можно сразу попробовать {GRADE_NAME[GRADE_CODES[GRADE_LEVEL[target] + 1]]}"
        return GradeDecision(grade_before=before, grade_after=target, changed=changed, message=msg,
                             upgrade_suggested=upgrade, next_change_at=self.next_change_at(c))

    def result_out(self, a: TestAttempt) -> AttemptResultOut:
        r = a.result or {}
        if not r:
            raise Conflict("Тест ещё не завершён", "ATTEMPT_NOT_FINISHED")
        return AttemptResultOut(
            id=a.id, status=a.status, score=a.score or 0, passed=bool(a.passed), specialization=a.specialization,
            target_grade=a.target_grade, decision=GradeDecision(**r["decision"]), by_skill=r["by_skill"],
            by_level=r["by_level"], items=r["items"], finished_at=a.finished_at)

    def history(self, c: CandidateProfile) -> list[AttemptSummary]:
        return [AttemptSummary.model_validate(a, from_attributes=True) for a in self.attempts.by_candidate(c.id)]

    def status(self, c: CandidateProfile) -> CategoryStatus:
        spec = c.specialization or (c.survey or {}).get("specialization")
        targets = []
        for g in GRADE_CODES:
            ok, _, msg = self.check_can_start(c, spec, g) if spec else (False, None, "Сначала пройдите опрос")
            targets.append(GradeTarget(grade=g, allowed=ok, reason=msg))
        nca = self.next_change_at(c)
        active = self.attempts.active(c.id)
        return CategoryStatus(
            specialization=c.specialization, grade=c.grade, category=category_label(c.specialization, c.grade),
            test_score=c.test_score, declared_grade=c.declared_grade, grade_assigned_at=c.grade_assigned_at,
            next_grade_change_at=nca, can_change_grade_now=(nca is None or nca <= utcnow()),
            survey_completed=bool(c.survey), targets=targets,
            history=[GradeHistoryOut.model_validate(h, from_attributes=True)
                     for h in CandidateRepository(self.db).grade_history(c.id)],
            active_attempt_id=active.id if active else None,
        )
