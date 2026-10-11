"""
Регулярные короткие задания от работодателей.

Система «периодически предлагает» кандидату задачу его категории: лента /short-tasks/feed
отдаёт активные задания специализации/грейда кандидата, которые он ещё не решал,
первым — самое свежее («задание недели»). Оценка работодателя (0..10) и сам факт
решения повышают компоненту «активность» в ранжировании -> профиль остаётся актуальным.
"""
from datetime import timezone

from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import BadRequest, Conflict, NotFound
from app.models import CandidateProfile, EmployerProfile, ShortTask, ShortTaskSubmission
from app.repositories.repos import CandidateRepository, ShortTaskRepository
from app.schemas.short_task import ShortTaskCreate, ShortTaskOut, SubmissionOut, SubmissionReview
from app.services.presenters import candidate_card, company_short, contact_basis


def _aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class ShortTaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ShortTaskRepository(db)

    def _out(self, t: ShortTask, count: int | None = None, my: str | None = None) -> ShortTaskOut:
        return ShortTaskOut(id=t.id, title=t.title, description=t.description, kind=t.kind,
                            specialization=t.specialization, grade=t.grade, deadline_at=t.deadline_at,
                            is_active=t.is_active, created_at=t.created_at, company=company_short(t.employer),
                            submissions_count=count, my_submission_status=my)

    def create(self, e: EmployerProfile, data: ShortTaskCreate) -> ShortTaskOut:
        t = self.repo.add(ShortTask(employer_id=e.id, **data.model_dump()))
        self.db.commit()
        self.db.refresh(t)
        return self._out(t, count=0)

    def mine(self, e: EmployerProfile) -> list[ShortTaskOut]:
        return [self._out(t, count=self.repo.submissions_count(t.id)) for t in self.repo.by_employer(e.id)]

    def close(self, e: EmployerProfile, task_id: int) -> ShortTaskOut:
        t = self.repo.get(task_id)
        if not t or t.employer_id != e.id:
            raise NotFound("Задание не найдено")
        t.is_active = False
        self.db.commit()
        return self._out(t, count=self.repo.submissions_count(t.id))

    def feed(self, c: CandidateProfile) -> list[ShortTaskOut]:
        if not c.specialization:
            return []  # сначала нужна категория по итогам теста
        now = utcnow()
        out = []
        for t in self.repo.feed(c.specialization, c.grade):
            if t.deadline_at and _aware(t.deadline_at) < now:
                continue
            sub = self.repo.submission(t.id, c.id)
            out.append(self._out(t, my=sub.status if sub else None))
        out.sort(key=lambda x: (x.my_submission_status is not None, -x.created_at.timestamp()))
        return out

    def submit(self, c: CandidateProfile, task_id: int, answer: str) -> SubmissionOut:
        t = self.repo.get(task_id)
        if not t or not t.is_active or t.specialization != c.specialization:
            raise NotFound("Задание не найдено")
        if t.deadline_at and _aware(t.deadline_at) < utcnow():
            raise BadRequest("Срок задания истёк", "DEADLINE_PASSED")
        if self.repo.submission(t.id, c.id):
            raise Conflict("Вы уже отправили решение", "ALREADY_SUBMITTED")
        s = ShortTaskSubmission(task_id=t.id, candidate_id=c.id, answer=answer)
        self.db.add(s)
        c.short_tasks_done += 1
        c.last_activity_at = utcnow()
        self.db.commit()
        return self._sub_out(s)

    def submissions(self, e: EmployerProfile, task_id: int) -> list[SubmissionOut]:
        t = self.repo.get(task_id)
        if not t or t.employer_id != e.id:
            raise NotFound("Задание не найдено")
        cands = CandidateRepository(self.db)
        return [self._sub_out(s, card=candidate_card(cands.get(s.candidate_id),
                                                     basis=contact_basis(self.db, e.id, s.candidate_id)))
                for s in self.repo.submissions(t.id)]

    def review(self, e: EmployerProfile, submission_id: int, data: SubmissionReview) -> SubmissionOut:
        s = self.db.get(ShortTaskSubmission, submission_id)
        if not s or s.task.employer_id != e.id:
            raise NotFound("Решение не найдено")
        s.employer_score, s.employer_feedback, s.status, s.reviewed_at = data.score, data.feedback, "reviewed", utcnow()
        self.db.flush()
        c = CandidateRepository(self.db).get(s.candidate_id)
        scores = self.repo.candidate_scores(c.id)
        c.short_tasks_avg = round(sum(scores) / len(scores), 2) if scores else None
        self.db.commit()
        return self._sub_out(s)

    @staticmethod
    def _sub_out(s: ShortTaskSubmission, card=None) -> SubmissionOut:
        return SubmissionOut(id=s.id, task_id=s.task_id, answer=s.answer, status=s.status,
                             employer_score=s.employer_score, employer_feedback=s.employer_feedback,
                             created_at=s.created_at, reviewed_at=s.reviewed_at, candidate=card)
