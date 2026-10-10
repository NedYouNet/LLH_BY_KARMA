"""Вакансии работодателя и самостоятельные отклики кандидатов (дополнительный сценарий)."""
import random

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import BadRequest, Conflict, NotFound
from app.models import Application, CandidateProfile, EmployerProfile, Vacancy
from app.reference import GRADE_LEVEL
from app.repositories.repos import ApplicationRepository, VacancyRepository
from app.schemas.testing import AssessmentPreview
from app.schemas.vacancy import (
    ApplicationOut, ApplicationStatusUpdate, VacancyCreate, VacancyOut, VacancyUpdate,
)
from app.services.presenters import candidate_card, contact_basis, vacancy_out
from app.services.testing_engine import build_items, public_item

APP_TRANSITIONS = {"sent": {"viewed", "accepted", "rejected"}, "viewed": {"accepted", "rejected"}}


class VacancyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VacancyRepository(db)
        self.apps = ApplicationRepository(db)

    # ------------------------------ вакансии ------------------------------
    def create(self, e: EmployerProfile, data: VacancyCreate) -> VacancyOut:
        v = self.repo.add(Vacancy(employer_id=e.id, **data.model_dump()))
        self.db.commit()
        self.db.refresh(v)
        return vacancy_out(v, applications_count=0)

    def owned(self, e: EmployerProfile, vacancy_id: int) -> Vacancy:
        v = self.repo.get(vacancy_id)
        if not v or v.employer_id != e.id:
            raise NotFound("Вакансия не найдена")
        return v

    def update(self, e: EmployerProfile, vacancy_id: int, data: VacancyUpdate) -> VacancyOut:
        v = self.owned(e, vacancy_id)
        changes = data.model_dump(exclude_unset=True)
        new_from = changes.get("salary_from", v.salary_from)
        new_to = changes.get("salary_to", v.salary_to)
        if new_to < new_from:
            raise BadRequest("salary_to должна быть не меньше salary_from", "SALARY_RANGE")
        for k, val in changes.items():
            setattr(v, k, val)
        self.db.commit()
        return vacancy_out(v, applications_count=self.apps.count_by_vacancy(v.id))

    def get_public(self, vacancy_id: int, candidate: CandidateProfile | None = None) -> VacancyOut:
        v = self.repo.get(vacancy_id)
        if not v or v.status != "active":
            raise NotFound("Вакансия не найдена или закрыта")
        my = self.apps.find(candidate.id, v.id) if candidate else None
        return vacancy_out(v, my_status=my.status if my else None)

    def list_public(self, candidate: CandidateProfile | None, **filters) -> tuple[int, list[VacancyOut]]:
        total, items = self.repo.list_public(**filters)
        mine = {a.vacancy_id: a.status for a in self.apps.by_candidate(candidate.id)} if candidate else {}
        return total, [vacancy_out(v, my_status=mine.get(v.id)) for v in items]

    def list_mine(self, e: EmployerProfile) -> list[VacancyOut]:
        return [vacancy_out(v, applications_count=self.apps.count_by_vacancy(v.id)) for v in self.repo.by_employer(e.id)]

    def assessment_preview(self, vacancy_id: int) -> AssessmentPreview:
        """Показываем жюри: как по описанию вакансии строится тест и что у двух кандидатов варианты разные."""
        v = self.repo.get(vacancy_id)
        if not v:
            raise NotFound("Вакансия не найдена")
        blueprint = {str(GRADE_LEVEL[v.grade]): 3}
        variants = [[public_item(i) for i in build_items(v.specialization, v.grade, random.randint(1, 10**9),
                                                          settings.test_questions_count, v.skills)] for _ in range(2)]
        return AssessmentPreview(vacancy_id=v.id, specialization=v.specialization, grade=v.grade, blueprint=blueprint,
                                 skills_focus=v.skills or [], sample_variants=variants)

    # ------------------------------ отклики ------------------------------
    def apply(self, c: CandidateProfile, vacancy_id: int, cover_letter: str | None) -> ApplicationOut:
        v = self.repo.get(vacancy_id)
        if not v or v.status != "active":
            raise NotFound("Вакансия не найдена или закрыта")
        if not c.consent_processing:
            raise BadRequest("Дайте согласие на обработку персональных данных в настройках", "CONSENT_REQUIRED")
        existing = self.apps.find(c.id, v.id)
        if existing and existing.status != "withdrawn":
            raise Conflict("Вы уже откликнулись на эту вакансию", "ALREADY_APPLIED")
        if existing:  # повторный отклик после отзыва
            existing.status, existing.cover_letter = "sent", cover_letter
            app = existing
        else:
            app = self.apps.add(Application(candidate_id=c.id, vacancy_id=v.id, cover_letter=cover_letter))
        c.last_activity_at = utcnow()
        self.db.commit()
        self.db.refresh(app)
        return self._app_out(app, for_employer=False)

    def my_applications(self, c: CandidateProfile) -> list[ApplicationOut]:
        return [self._app_out(a, for_employer=False) for a in self.apps.by_candidate(c.id)]

    def withdraw(self, c: CandidateProfile, app_id: int) -> ApplicationOut:
        app = self.apps.get(app_id)
        if not app or app.candidate_id != c.id:
            raise NotFound("Отклик не найден")
        if app.status not in ("sent", "viewed"):
            raise Conflict("Отклик уже обработан работодателем", "INVALID_STATUS_TRANSITION")
        app.status = "withdrawn"
        self.db.commit()
        return self._app_out(app, for_employer=False)

    def employer_applications(self, e: EmployerProfile, vacancy_id: int | None) -> list[ApplicationOut]:
        apps = self.apps.by_vacancy(self.owned(e, vacancy_id).id) if vacancy_id else self.apps.by_employer(e.id)
        return [self._app_out(a, for_employer=True, employer_id=e.id) for a in apps if a.status != "withdrawn"]

    def set_status(self, e: EmployerProfile, app_id: int, data: ApplicationStatusUpdate) -> ApplicationOut:
        app = self.apps.get(app_id)
        if not app or app.vacancy.employer_id != e.id:
            raise NotFound("Отклик не найден")
        if data.status not in APP_TRANSITIONS.get(app.status, set()):
            raise Conflict(f"Нельзя перевести отклик из «{app.status}» в «{data.status}»", "INVALID_STATUS_TRANSITION")
        app.status = data.status
        if data.comment:
            app.employer_comment = data.comment
        self.db.commit()
        return self._app_out(app, for_employer=True, employer_id=e.id)

    def _app_out(self, a: Application, for_employer: bool, employer_id: int | None = None) -> ApplicationOut:
        card = None
        if for_employer:
            # Кандидат САМ откликнулся -> контакты для этого работодателя открыты (правило ТЗ №2)
            card = candidate_card(a.candidate, basis=contact_basis(self.db, employer_id, a.candidate_id))
        return ApplicationOut(id=a.id, status=a.status, cover_letter=a.cover_letter,
                              employer_comment=a.employer_comment, created_at=a.created_at, updated_at=a.updated_at,
                              vacancy=vacancy_out(a.vacancy), candidate=card)
