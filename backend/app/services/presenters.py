"""
«Презентеры»: превращают модели БД в схемы ответа С УЧЁТОМ ПРАВ ДОСТУПА.

Самое важное правило ТЗ живёт здесь и в `contact_basis`:
  контакты кандидата раскрываются работодателю ТОЛЬКО если
    (а) кандидат принял его приглашение, или
    (б) кандидат сам откликнулся на его вакансию.
Иначе поле `contacts` = null, а имя сокращено до «Иван П.».
"""
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models import CandidateProfile, EmployerProfile, Invitation, Vacancy
from app.reference import category_label
from app.repositories.repos import ApplicationRepository, ContactLogRepository, InvitationRepository
from app.schemas.candidate import CandidateCard, CandidateContacts, CandidateDetail, Privacy
from app.schemas.common import SALARY_TYPE_LABEL
from app.schemas.employer import CompanyShort
from app.schemas.invitation import InvitationCandidateShort, InvitationOut
from app.schemas.vacancy import VacancyOut
from app.services.matching_engine import MatchResult


def contact_basis(db: Session, employer_id: int, candidate_id: int) -> str | None:
    """Основание для раскрытия контактов или None, если раскрывать нельзя."""
    inv = InvitationRepository(db).accepted_between(employer_id, candidate_id)
    if inv:
        return f"invitation_accepted:{inv.id}"
    app = ApplicationRepository(db).candidate_applied_to_employer(candidate_id, employer_id)
    if app:
        return f"application:{app.id}"
    return None


def contact_basis_map(db: Session, employer_id: int, candidate_ids: list[int]) -> dict[int, str]:
    """То же, что contact_basis, но для целой страницы выдачи двумя запросами вместо 2×N."""
    out = {cid: f"application:{aid}" for cid, aid in
           ApplicationRepository(db).applied_map(employer_id, candidate_ids).items()}
    out.update({cid: f"invitation_accepted:{iid}" for cid, iid in
                InvitationRepository(db).accepted_map(employer_id, candidate_ids).items()})
    return out


def log_contact_access(db: Session, employer_id: int, candidate_id: int, basis: str) -> None:
    ContactLogRepository(db).log(employer_id, candidate_id, basis, utcnow())


def privacy_of(c: CandidateProfile) -> Privacy:
    return Privacy(**(c.privacy or {}))


def display_name(c: CandidateProfile, reveal: bool) -> str:
    name = (c.full_name or "").strip()
    if not name:
        return f"Кандидат #{c.id}"
    if reveal or privacy_of(c).show_full_name:
        return name
    parts = name.split()
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[1][0]}."  # «Иван П.»


def _fsp_verification(c: CandidateProfile) -> str:
    ach = c.fsp_achievements or []
    if not ach:
        return "none"
    return "verified" if all(a.get("verification_status") == "verified" for a in ach) else "demo"


def _contacts(c: CandidateProfile) -> CandidateContacts:
    return CandidateContacts(full_name=c.full_name, email=c.contact_email or (c.user.email if c.user else None),
                             phone=c.phone, telegram=c.telegram)


def candidate_card(c: CandidateProfile, *, basis: str | None, match: MatchResult | None = None,
                   invitation_status: str | None = None, in_shortlist: bool = False) -> CandidateCard:
    reveal = basis is not None
    pr = privacy_of(c)
    return CandidateCard(
        id=c.id, display_name=display_name(c, reveal), city=c.city if (pr.show_city or reveal) else None,
        specialization=c.effective_specialization, grade=c.effective_grade,
        category=category_label(c.effective_specialization, c.effective_grade),
        category_id=f"{c.effective_specialization}:{c.effective_grade}"
        if c.effective_specialization and c.effective_grade else None,
        grade_verified=c.grade_verified,
        grade_status_label="Подтверждён тестом" if c.grade_verified else "Не подтверждён: заявлен кандидатом",
        test_score=c.test_score if c.grade_verified else None,
        test_completed_at=(c.grade_changed_at or c.grade_assigned_at) if c.grade_verified else None,
        experience_years=c.experience_years, skills=c.skills or [],
        matched_skills=match.matched_skills if match else [],
        work_format=c.work_format, has_fsp=bool(c.fsp_achievements), fsp_id=c.fsp_id, fsp_rank=c.fsp_rank,
        fsp_verification=_fsp_verification(c),
        match_score=match.score if match else None, reasons=match.reasons if match else [],
        breakdown=match.breakdown if match else None,
        contacts_visible=reveal, contacts=_contacts(c) if reveal else None,
        invitation_status=invitation_status, in_shortlist=in_shortlist,
    )


def candidate_detail(c: CandidateProfile, *, basis: str | None, match: MatchResult | None = None,
                     invitation_status: str | None = None, in_shortlist: bool = False) -> CandidateDetail:
    card = candidate_card(c, basis=basis, match=match, invitation_status=invitation_status, in_shortlist=in_shortlist)
    pr = privacy_of(c)
    reveal = basis is not None
    return CandidateDetail(
        **card.model_dump(),
        about=c.about if (pr.show_about or reveal) else None,
        soft_skills=c.soft_skills or [], team_roles=c.team_roles or [], skill_scores=c.skill_scores or {},
        fsp_achievements=(c.fsp_achievements or []) if (pr.show_fsp_achievements or reveal) else [],
        fsp_score=c.fsp_score, last_activity_at=c.last_activity_at, short_tasks_done=c.short_tasks_done,
        short_tasks_avg=c.short_tasks_avg,
        contacts_hidden_reason=None if reveal else
        "Контакты откроются, когда кандидат примет ваше приглашение или откликнется на вашу вакансию",
    )


def company_short(e: EmployerProfile) -> CompanyShort:
    return CompanyShort(id=e.id, company_name=e.company_name, industry=e.industry, website=e.website,
                        city=e.city, trust_level=e.trust_level)


def vacancy_out(v: Vacancy, applications_count: int | None = None, my_status: str | None = None) -> VacancyOut:
    return VacancyOut(
        id=v.id, title=v.title, description=v.description, team_description=v.team_description,
        specialization=v.specialization, grade=v.grade, category=category_label(v.specialization, v.grade),
        skills=v.skills or [], salary_from=v.salary_from, salary_to=v.salary_to, salary_type=v.salary_type,
        salary_type_label=SALARY_TYPE_LABEL.get(v.salary_type, v.salary_type), work_format=v.work_format,
        city=v.city, status=v.status, company=company_short(v.employer), created_at=v.created_at,
        updated_at=v.updated_at, applications_count=applications_count, my_application_status=my_status,
    )


def invitation_out(inv: Invitation, reveal_name: bool = False) -> InvitationOut:
    c = inv.candidate
    return InvitationOut(
        id=inv.id, status=inv.status, candidate_id=inv.candidate_id, employer_id=inv.employer_id,
        position_title=inv.position_title, message=inv.message,
        salary_from=inv.salary_from, salary_to=inv.salary_to, salary_type=inv.salary_type,
        salary_type_label=SALARY_TYPE_LABEL.get(inv.salary_type, inv.salary_type),
        contacts_revoked=inv.contacts_revoked_at is not None, contact_method=inv.contact_method,
        vacancy_id=inv.vacancy_id, company=company_short(inv.employer),
        candidate=InvitationCandidateShort(id=c.id, display_name=display_name(c, reveal_name or inv.status == "accepted"),
                                           category=category_label(c.effective_specialization, c.effective_grade)),
        match_score=inv.match_score, match_reasons=inv.match_reasons or [], candidate_reply=inv.candidate_reply,
        created_at=inv.created_at, viewed_at=inv.viewed_at, responded_at=inv.responded_at,
        updated_at=inv.updated_at,
    )
