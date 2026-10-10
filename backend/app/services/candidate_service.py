"""Личный кабинет кандидата: профиль, опрос, резюме, согласия, приватность, ФСП."""
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import BadRequest, Conflict, NotFound
from app.models import CandidateProfile
from app.reference import category_label
from app.schemas.candidate import (
    CandidateProfileOut, CandidateProfileUpdate, Consents, ParsedResume, Privacy, ResumeParseOut, SurveyIn,
)
from app.repositories.repos import CandidateRepository
from app.services import fsp_service
from app.services.ml_client import extract_pdf_text, fallback_parse, parse_resume_in_process, parse_resume_via_ml

MAX_PDF_BYTES = 5 * 1024 * 1024


def profile_out(c: CandidateProfile) -> CandidateProfileOut:
    data = CandidateProfileOut.model_validate(c, from_attributes=True)
    data.category = category_label(c.specialization, c.grade)
    return data


class CandidateService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CandidateRepository(db)

    def _touch(self, c: CandidateProfile) -> None:
        c.last_activity_at = utcnow()

    def update_profile(self, c: CandidateProfile, data: CandidateProfileUpdate) -> CandidateProfile:
        # exclude_unset: меняем только поля, которые фронт реально прислал
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(c, field, value)
        self._touch(c)
        self.db.commit()
        return c

    def submit_survey(self, c: CandidateProfile, data: SurveyIn) -> CandidateProfile:
        c.industry = data.industry
        if data.experience_years is not None:
            c.experience_years = data.experience_years
        if data.skills:
            c.skills = data.skills
        if data.team_roles:
            c.team_roles = data.team_roles
        if data.work_format:
            c.work_format = data.work_format
        c.declared_grade = data.declared_grade
        c.declared_specialization = data.specialization
        # Специализацию из опроса запоминаем отдельно: категорию присвоит только тест
        c.survey = {**data.model_dump(), "submitted_at": utcnow().isoformat()}
        self._touch(c)
        self.db.commit()
        return c

    def set_consents(self, c: CandidateProfile, data: Consents) -> CandidateProfile:
        if data.consent_publication and not data.consent_processing:
            raise BadRequest("Нельзя публиковать профиль без согласия на обработку данных", "CONSENT_REQUIRED")
        c.consent_processing = data.consent_processing
        c.consent_publication = data.consent_publication
        c.consent_at = utcnow()
        self.db.commit()
        return c

    def set_privacy(self, c: CandidateProfile, data: Privacy) -> CandidateProfile:
        c.privacy = data.model_dump()
        self.db.commit()
        return c

    def parse_resume(self, c: CandidateProfile, pdf: bytes, filename: str, apply: bool) -> ResumeParseOut:
        if len(pdf) > MAX_PDF_BYTES:
            raise BadRequest("PDF больше 5 МБ", "FILE_TOO_LARGE")
        if not pdf.startswith(b"%PDF"):
            raise BadRequest("Файл не похож на PDF", "NOT_PDF")
        text = extract_pdf_text(pdf)
        ml = parse_resume_in_process(pdf, text, filename) or parse_resume_via_ml(text)
        source = "ml" if ml else "fallback"
        fields = ParsedResume(**{k: v for k, v in (ml or fallback_parse(text)).items() if k in ParsedResume.model_fields})
        if apply:
            # Заполняем только пустые поля — не затираем то, что кандидат уже ввёл руками
            mapping = {"full_name": fields.full_name, "phone": fields.phone, "telegram": fields.telegram,
                       "city": fields.city, "about": fields.about}
            for k, v in mapping.items():
                if v and not getattr(c, k):
                    setattr(c, k, v)
            if fields.skills:
                c.skills = list(dict.fromkeys([*(c.skills or []), *fields.skills]))[:40]
            if fields.soft_skills and not c.soft_skills:
                c.soft_skills = fields.soft_skills
            if fields.experience_years is not None and not c.experience_years:
                c.experience_years = fields.experience_years
            c.resume_text = text[:20000] or c.resume_text
            self._touch(c)
            self.db.commit()
        return ResumeParseOut(source=source, fields=fields, applied=apply)

    def link_fsp(self, c: CandidateProfile, fsp_id: str) -> CandidateProfile:
        fsp_id = fsp_id.strip()
        other = self.repo.by_fsp_id(fsp_id)
        if other and other.id != c.id:
            raise Conflict("Этот ФСП ID уже привязан к другому профилю", "FSP_ID_TAKEN")
        participant = fsp_service.registry.get_participant(fsp_id)
        if participant is None:
            raise NotFound("Участник с таким ФСП ID не найден в реестре", "FSP_NOT_FOUND")
        c.fsp_id = fsp_id
        c.fsp_achievements = participant["achievements"]
        c.fsp_score = fsp_service.compute_fsp_score(participant["achievements"])
        c.fsp_rank = participant.get("sport_rank")
        c.fsp_synced_at = utcnow()
        self._touch(c)
        self.db.commit()
        return c

    def unlink_fsp(self, c: CandidateProfile) -> CandidateProfile:
        c.fsp_id, c.fsp_achievements, c.fsp_score, c.fsp_synced_at, c.fsp_rank = None, [], 0.0, None, None
        self.db.commit()
        return c

    @staticmethod
    def onboarding(c: CandidateProfile) -> dict:
        """Чек-лист обязательного пути — фронт показывает прогресс-бар."""
        return {
            "profile_filled": bool(c.full_name and c.skills),
            "survey_completed": bool(c.survey),
            "test_passed": bool(c.grade),
            "consents_given": bool(c.consent_processing and c.consent_publication),
            "fsp_linked": bool(c.fsp_id),
            "visible_to_employers": c.is_searchable,
        }
