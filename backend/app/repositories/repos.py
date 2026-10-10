"""Конкретные репозитории. Каждый метод — один понятный запрос."""
from datetime import datetime

from sqlalchemy import and_, case, func, or_, select

from app.models import (
    EmployerNeed, Application, CandidateProfile, ContactAccessLog, EmployerProfile, GradeHistory, Invitation,
    QuestionStat, ShortlistItem, ShortTask, ShortTaskSubmission, TestAttempt, User, Vacancy,
)
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))


class CandidateRepository(BaseRepository[CandidateProfile]):
    model = CandidateProfile

    def by_user(self, user_id: int) -> CandidateProfile | None:
        return self.db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))

    def by_fsp_id(self, fsp_id: str) -> CandidateProfile | None:
        return self.db.scalar(select(CandidateProfile).where(CandidateProfile.fsp_id == fsp_id))

    # Категория для выдачи: подтверждённая тестом, иначе заявленная кандидатом (см. CandidateProfile)
    _verified = and_(CandidateProfile.grade.is_not(None), CandidateProfile.specialization.is_not(None))
    eff_spec = case((_verified, CandidateProfile.specialization), else_=CandidateProfile.declared_specialization)
    eff_grade = case((_verified, CandidateProfile.grade), else_=CandidateProfile.declared_grade)

    def searchable(self, specialization: str | None = None, grades: list[str] | None = None,
                   only_verified: bool = False) -> list[CandidateProfile]:
        """
        Пул для подборки: согласия + категория. Кандидаты без теста тоже в пуле (с заявленной категорией),
        ранжирование опустит их ниже и пометит «не подтверждён». only_verified=True — только прошедшие тест.
        """
        q = select(CandidateProfile).join(User).where(
            CandidateProfile.consent_publication.is_(True),
            CandidateProfile.consent_processing.is_(True),
            self.eff_spec.is_not(None),
            self.eff_grade.is_not(None),
            User.is_active.is_(True),
        )
        if only_verified:
            q = q.where(self._verified)
        if specialization:
            q = q.where(self.eff_spec == specialization)
        if grades:
            q = q.where(self.eff_grade.in_(grades))
        return list(self.db.scalars(q))

    def category_stats(self) -> list[tuple]:
        """(специализация, грейд, всего, подтверждено тестом, с ФСП, средний балл подтверждённых) по видимым."""
        verified_int = case((self._verified, 1), else_=0)
        q = (select(self.eff_spec, self.eff_grade, func.count(), func.sum(verified_int),
                    func.sum(case((CandidateProfile.fsp_score > 0, 1), else_=0)),
                    func.avg(case((self._verified, CandidateProfile.test_score), else_=None)))
             .where(CandidateProfile.consent_publication.is_(True), CandidateProfile.consent_processing.is_(True),
                    self.eff_spec.is_not(None), self.eff_grade.is_not(None))
             .group_by(self.eff_spec, self.eff_grade))
        return list(self.db.execute(q).all())

    def grade_history(self, candidate_id: int) -> list[GradeHistory]:
        return list(self.db.scalars(select(GradeHistory).where(GradeHistory.candidate_id == candidate_id)
                                    .order_by(GradeHistory.changed_at.desc())))


class EmployerRepository(BaseRepository[EmployerProfile]):
    model = EmployerProfile

    def by_user(self, user_id: int) -> EmployerProfile | None:
        return self.db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))


class VacancyRepository(BaseRepository[Vacancy]):
    model = Vacancy

    def list_public(self, specialization=None, grade=None, q=None, salary_min=None, work_format=None,
                    offset=0, limit=20) -> tuple[int, list[Vacancy]]:
        stmt = select(Vacancy).where(Vacancy.status == "active")
        if specialization:
            stmt = stmt.where(Vacancy.specialization == specialization)
        if grade:
            stmt = stmt.where(Vacancy.grade == grade)
        if work_format:
            stmt = stmt.where(Vacancy.work_format == work_format)
        if salary_min:
            stmt = stmt.where(Vacancy.salary_to >= salary_min)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(or_(func.lower(Vacancy.title).like(like), func.lower(Vacancy.description).like(like)))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = list(self.db.scalars(stmt.order_by(Vacancy.created_at.desc()).offset(offset).limit(limit)))
        return total, items

    def by_employer(self, employer_id: int) -> list[Vacancy]:
        return list(self.db.scalars(select(Vacancy).where(Vacancy.employer_id == employer_id)
                                    .order_by(Vacancy.created_at.desc())))


class ApplicationRepository(BaseRepository[Application]):
    model = Application

    def find(self, candidate_id: int, vacancy_id: int) -> Application | None:
        return self.db.scalar(select(Application).where(Application.candidate_id == candidate_id,
                                                        Application.vacancy_id == vacancy_id))

    def by_candidate(self, candidate_id: int) -> list[Application]:
        return list(self.db.scalars(select(Application).where(Application.candidate_id == candidate_id)
                                    .order_by(Application.created_at.desc())))

    def by_vacancy(self, vacancy_id: int) -> list[Application]:
        return list(self.db.scalars(select(Application).where(Application.vacancy_id == vacancy_id)
                                    .order_by(Application.created_at.desc())))

    def by_employer(self, employer_id: int) -> list[Application]:
        return list(self.db.scalars(select(Application).join(Vacancy).where(Vacancy.employer_id == employer_id)
                                    .order_by(Application.created_at.desc())))

    def count_by_vacancy(self, vacancy_id: int) -> int:
        return self.count(Application.vacancy_id == vacancy_id)

    def candidate_applied_to_employer(self, candidate_id: int, employer_id: int) -> Application | None:
        return self.db.scalar(select(Application).join(Vacancy).where(
            Application.candidate_id == candidate_id, Vacancy.employer_id == employer_id,
            Application.status != "withdrawn").limit(1))

    def applied_map(self, employer_id: int, candidate_ids: list[int]) -> dict[int, int]:
        """{candidate_id: application_id} одним запросом — для страницы выдачи (без N+1)."""
        if not candidate_ids:
            return {}
        rows = self.db.execute(select(Application.candidate_id, Application.id).join(Vacancy).where(
            Application.candidate_id.in_(candidate_ids), Vacancy.employer_id == employer_id,
            Application.status != "withdrawn")).all()
        return {cid: aid for cid, aid in rows}


class InvitationRepository(BaseRepository[Invitation]):
    model = Invitation

    def for_employer(self, employer_id: int, status: str | None = None) -> list[Invitation]:
        q = select(Invitation).where(Invitation.employer_id == employer_id)
        if status:
            q = q.where(Invitation.status == status)
        return list(self.db.scalars(q.order_by(Invitation.created_at.desc())))

    def for_candidate(self, candidate_id: int, status: str | None = None) -> list[Invitation]:
        q = select(Invitation).where(Invitation.candidate_id == candidate_id, Invitation.status != "withdrawn")
        if status:
            q = q.where(Invitation.status == status)
        return list(self.db.scalars(q.order_by(Invitation.created_at.desc())))

    def open_between(self, employer_id: int, candidate_id: int) -> Invitation | None:
        """Есть ли уже «живое» приглашение (защита от спама одному кандидату)."""
        return self.db.scalar(select(Invitation).where(
            Invitation.employer_id == employer_id, Invitation.candidate_id == candidate_id,
            Invitation.status.in_(["sent", "viewed"])).limit(1))

    def accepted_between(self, employer_id: int, candidate_id: int) -> Invitation | None:
        return self.db.scalar(select(Invitation).where(
            Invitation.employer_id == employer_id, Invitation.candidate_id == candidate_id,
            Invitation.status == "accepted", Invitation.contacts_revoked_at.is_(None)).limit(1))

    def accepted_map(self, employer_id: int, candidate_ids: list[int]) -> dict[int, int]:
        """{candidate_id: invitation_id} принятых и не закрытых кандидатом приглашений — одним запросом."""
        if not candidate_ids:
            return {}
        rows = self.db.execute(select(Invitation.candidate_id, Invitation.id).where(
            Invitation.employer_id == employer_id, Invitation.candidate_id.in_(candidate_ids),
            Invitation.status == "accepted", Invitation.contacts_revoked_at.is_(None))).all()
        return {cid: iid for cid, iid in rows}

    def latest_status_map(self, employer_id: int, candidate_ids: list[int]) -> dict[int, str]:
        if not candidate_ids:
            return {}
        rows = self.db.execute(select(Invitation.candidate_id, Invitation.status, Invitation.created_at)
                               .where(Invitation.employer_id == employer_id,
                                      Invitation.candidate_id.in_(candidate_ids))
                               .order_by(Invitation.created_at)).all()
        return {cid: st for cid, st, _ in rows}  # последний по времени перезапишет


class AttemptRepository(BaseRepository[TestAttempt]):
    model = TestAttempt

    def active(self, candidate_id: int) -> TestAttempt | None:
        return self.db.scalar(select(TestAttempt).where(TestAttempt.candidate_id == candidate_id,
                                                        TestAttempt.status == "in_progress").limit(1))

    def last_for_target(self, candidate_id: int, spec: str, grade: str) -> TestAttempt | None:
        return self.db.scalar(select(TestAttempt).where(
            TestAttempt.candidate_id == candidate_id, TestAttempt.specialization == spec,
            TestAttempt.target_grade == grade).order_by(TestAttempt.started_at.desc()).limit(1))

    def by_candidate(self, candidate_id: int) -> list[TestAttempt]:
        return list(self.db.scalars(select(TestAttempt).where(TestAttempt.candidate_id == candidate_id)
                                    .order_by(TestAttempt.started_at.desc())))

    def bump_stat(self, template_id: str, frac: float, attempt_score: float) -> None:
        stat = self.db.get(QuestionStat, template_id)
        if stat is None:
            stat = QuestionStat(template_id=template_id, shown=0, correct=0, sum_score_correct=0.0, sum_score_wrong=0.0)
            self.db.add(stat)
            self.db.flush()  # шаблон может встретиться в попытке дважды — запись должна быть видна сразу
        stat.shown += 1
        if frac >= 1:
            stat.correct += 1
            stat.sum_score_correct += attempt_score
        else:
            stat.sum_score_wrong += attempt_score


class ShortlistRepository(BaseRepository[ShortlistItem]):
    model = ShortlistItem

    def find(self, employer_id: int, candidate_id: int) -> ShortlistItem | None:
        return self.db.scalar(select(ShortlistItem).where(ShortlistItem.employer_id == employer_id,
                                                          ShortlistItem.candidate_id == candidate_id))

    def for_employer(self, employer_id: int) -> list[ShortlistItem]:
        return list(self.db.scalars(select(ShortlistItem).where(ShortlistItem.employer_id == employer_id)
                                    .order_by(ShortlistItem.created_at.desc())))

    def ids_for_employer(self, employer_id: int) -> set[int]:
        return set(self.db.scalars(select(ShortlistItem.candidate_id).where(ShortlistItem.employer_id == employer_id)))


class ContactLogRepository(BaseRepository[ContactAccessLog]):
    model = ContactAccessLog

    def log(self, employer_id: int, candidate_id: int, basis: str, at: datetime) -> None:
        self.add(ContactAccessLog(employer_id=employer_id, candidate_id=candidate_id, basis=basis, accessed_at=at))


class ShortTaskRepository(BaseRepository[ShortTask]):
    model = ShortTask

    def by_employer(self, employer_id: int) -> list[ShortTask]:
        return list(self.db.scalars(select(ShortTask).where(ShortTask.employer_id == employer_id)
                                    .order_by(ShortTask.created_at.desc())))

    def feed(self, specialization: str, grade: str | None) -> list[ShortTask]:
        q = select(ShortTask).where(ShortTask.is_active.is_(True), ShortTask.specialization == specialization)
        if grade:
            q = q.where(or_(ShortTask.grade.is_(None), ShortTask.grade == grade))
        return list(self.db.scalars(q.order_by(ShortTask.created_at.desc())))

    def submission(self, task_id: int, candidate_id: int) -> ShortTaskSubmission | None:
        return self.db.scalar(select(ShortTaskSubmission).where(ShortTaskSubmission.task_id == task_id,
                                                                ShortTaskSubmission.candidate_id == candidate_id))

    def submissions(self, task_id: int) -> list[ShortTaskSubmission]:
        return list(self.db.scalars(select(ShortTaskSubmission).where(ShortTaskSubmission.task_id == task_id)
                                    .order_by(ShortTaskSubmission.created_at.desc())))

    def submissions_count(self, task_id: int) -> int:
        return self.db.scalar(select(func.count()).select_from(ShortTaskSubmission)
                              .where(ShortTaskSubmission.task_id == task_id)) or 0

    def candidate_scores(self, candidate_id: int) -> list[float]:
        return [s for s in self.db.scalars(select(ShortTaskSubmission.employer_score).where(
            ShortTaskSubmission.candidate_id == candidate_id, ShortTaskSubmission.employer_score.is_not(None)))]


class NeedRepository(BaseRepository[EmployerNeed]):
    model = EmployerNeed

    def by_employer(self, employer_id: int) -> list[EmployerNeed]:
        return list(self.db.scalars(select(EmployerNeed).where(EmployerNeed.employer_id == employer_id)
                                    .order_by(EmployerNeed.updated_at.desc())))
