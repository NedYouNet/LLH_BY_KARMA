"""
Приглашения — главная механика продукта.

Машина состояний (кто и какой переход может сделать):

    sent ──(кандидат открыл)──> viewed ──(кандидат)──> accepted   => контакты раскрываются
      │                           │      └─(кандидат)──> declined
      └──────(работодатель)───────┴──────────────────────> withdrawn

Любой другой переход -> 409 INVALID_STATUS_TRANSITION.
"""
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import BadRequest, Conflict, NotFound
from app.models import CandidateProfile, EmployerProfile, Invitation, Vacancy
from app.repositories.repos import CandidateRepository, InvitationRepository
from app.schemas.invitation import InvitationCreate, InvitationOut
from app.services.ats_service import AtsService
from app.services.email_service import send_invitation_email
from app.services.matching_engine import SearchCriteria, score_candidate
from app.services.matching_service import criteria_from_vacancy
from app.services.presenters import invitation_out

TRANSITIONS = {
    "candidate": {"sent": {"viewed", "accepted", "declined"}, "viewed": {"accepted", "declined"}},
    "employer": {"sent": {"withdrawn"}, "viewed": {"withdrawn"}},
}


class InvitationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvitationRepository(db)

    def create(self, employer: EmployerProfile, data: InvitationCreate) -> InvitationOut:
        if not (employer.company_name or "").strip():
            raise BadRequest("Заполните название компании в профиле — кандидат должен видеть, кто его приглашает",
                             "COMPANY_PROFILE_INCOMPLETE")
        contact = data.contact_method or employer.contact or employer.contact_email
        if not contact:
            raise BadRequest("Укажите способ связи в приглашении или в профиле компании", "CONTACT_REQUIRED",
                             extra={"fields": {"contact_method": "Обязательное поле"}})
        c = CandidateRepository(self.db).get(data.candidate_id)
        if not c or not c.is_searchable:
            raise NotFound("Кандидат не найден или скрыл профиль")
        vacancy = None
        if data.vacancy_id:
            vacancy = self.db.get(Vacancy, data.vacancy_id)
            if not vacancy or vacancy.employer_id != employer.id:
                raise NotFound("Вакансия не найдена среди ваших")
        if self.repo.open_between(employer.id, c.id):
            raise Conflict("Вы уже отправили приглашение этому кандидату — дождитесь ответа", "INVITATION_EXISTS")

        crit = criteria_from_vacancy(vacancy) if vacancy else SearchCriteria()
        match = score_candidate(c, crit)  # снимок «почему вы» — кандидат увидит в приглашении
        inv = self.repo.add(Invitation(
            employer_id=employer.id, candidate_id=c.id, vacancy_id=data.vacancy_id,
            position_title=data.position_title or (vacancy.title if vacancy else "Предложение о работе"),
            message=data.message, salary_from=data.salary_from,
            salary_to=data.salary_to, salary_type=data.salary_type, contact_method=contact, status="sent",
            match_score=match.score, match_reasons=match.reasons))
        self.db.commit()
        if c.user:
            send_invitation_email(c.contact_email or c.user.email, employer.company_name, inv.position_title,
                                  data.salary_from, data.salary_to, data.salary_type)
        return invitation_out(inv)

    def list_for_employer(self, employer: EmployerProfile, status: str | None) -> list[InvitationOut]:
        return [invitation_out(i) for i in self.repo.for_employer(employer.id, status)]

    def list_for_candidate(self, c: CandidateProfile, status: str | None) -> list[InvitationOut]:
        return [invitation_out(i, reveal_name=True) for i in self.repo.for_candidate(c.id, status)]

    def _owned(self, inv_id: int, *, candidate: CandidateProfile | None = None,
               employer: EmployerProfile | None = None) -> Invitation:
        inv = self.repo.get(inv_id)
        if not inv or (candidate and inv.candidate_id != candidate.id) or (employer and inv.employer_id != employer.id):
            raise NotFound("Приглашение не найдено")  # чужое = «не существует» (не раскрываем факт наличия)
        return inv

    def get_for_candidate(self, c: CandidateProfile, inv_id: int) -> InvitationOut:
        inv = self._owned(inv_id, candidate=c)
        if inv.status == "withdrawn":
            raise NotFound("Приглашение отозвано работодателем", "INVITATION_WITHDRAWN")
        if inv.status == "sent":  # открыл -> «просмотрено»
            inv.status, inv.viewed_at = "viewed", utcnow()
            self.db.commit()
        return invitation_out(inv, reveal_name=True)

    def get_for_employer(self, e: EmployerProfile, inv_id: int) -> InvitationOut:
        return invitation_out(self._owned(inv_id, employer=e))

    def _move(self, inv: Invitation, actor: str, new_status: str) -> None:
        allowed = TRANSITIONS[actor].get(inv.status, set())
        if new_status not in allowed:
            raise Conflict(f"Нельзя перевести приглашение из «{inv.status}» в «{new_status}»",
                           "INVALID_STATUS_TRANSITION")
        inv.status = new_status

    def respond(self, c: CandidateProfile, inv_id: int, accept: bool, reply: str | None,
                background=None) -> InvitationOut:
        """background — FastAPI BackgroundTasks: событие в ATS работодателя уйдёт после ответа кандидату."""
        inv = self._owned(inv_id, candidate=c)
        self._move(inv, "candidate", "accepted" if accept else "declined")
        now = utcnow()
        inv.viewed_at = inv.viewed_at or now
        inv.responded_at = now
        inv.candidate_reply = reply
        c.last_activity_at = now
        self.db.commit()
        if accept:
            job = AtsService(self.db).prepare_invitation_accepted(inv)
            if job is not None:
                background.add_task(job) if background is not None else job()
        return invitation_out(inv, reveal_name=True)

    def set_contact_access(self, c: CandidateProfile, inv_id: int, granted: bool) -> InvitationOut:
        """
        Отзыв доступа к контактам (плюс по ответам организаторов). Работает только для принятого приглашения:
        после отзыва работодатель снова видит «Иван П.» без контактов. То, что он уже успел увидеть,
        отозвать технически нельзя — поэтому каждое раскрытие и так пишется в журнал (contact-access-log).
        """
        inv = self._owned(inv_id, candidate=c)
        if inv.status != "accepted":
            raise Conflict("Управлять доступом к контактам можно только по принятому приглашению",
                           "INVALID_STATUS_TRANSITION")
        inv.contacts_revoked_at = None if granted else utcnow()
        self.db.commit()
        return invitation_out(inv, reveal_name=True)

    def withdraw(self, e: EmployerProfile, inv_id: int) -> InvitationOut:
        inv = self._owned(inv_id, employer=e)
        self._move(inv, "employer", "withdrawn")
        self.db.commit()
        return invitation_out(inv)
