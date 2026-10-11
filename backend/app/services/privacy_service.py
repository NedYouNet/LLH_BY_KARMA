"""
Права субъекта персональных данных (152-ФЗ, ст. 14 и 21):
  - узнать, какие данные о нём хранятся (выгрузка всех данных одним JSON);
  - узнать, кому раскрывались его контакты (журнал contact_access_log);
  - отозвать согласие и удалить свои данные (удаление аккаунта со всеми связанными записями).
"""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import Unauthorized
from app.core.security import verify_password
from app.models import AuthEvent, CandidateProfile, ContactAccessLog, EmployerProfile, User
from app.repositories.repos import CandidateRepository
from app.services.candidate_service import profile_out
from app.services.invitation_service import InvitationService
from app.services.testing_service import TestingService
from app.services.vacancy_service import VacancyService


class PrivacyService:
    def __init__(self, db: Session):
        self.db = db

    def contact_access_log(self, c: CandidateProfile) -> list[dict]:
        rows = self.db.execute(
            select(ContactAccessLog, EmployerProfile.company_name)
            .join(EmployerProfile, EmployerProfile.id == ContactAccessLog.employer_id)
            .where(ContactAccessLog.candidate_id == c.id).order_by(ContactAccessLog.accessed_at.desc())).all()
        return [{"company_name": name, "basis": log.basis, "accessed_at": log.accessed_at} for log, name in rows]

    def export(self, c: CandidateProfile) -> dict:
        return {
            "exported_at": utcnow(),
            "account": {"email": c.user.email, "created_at": c.user.created_at, "role": c.user.role},
            "profile": profile_out(c).model_dump(),
            "grade_history": [h.model_dump() for h in TestingService(self.db).status(c).history],
            "test_attempts": [a.model_dump() for a in TestingService(self.db).history(c)],
            "invitations": [i.model_dump() for i in InvitationService(self.db).list_for_candidate(c, None)],
            "applications": [a.model_dump(exclude={"vacancy": {"description"}})
                             for a in VacancyService(self.db).my_applications(c)],
            "contact_access_log": self.contact_access_log(c),
        }

    def delete_account(self, user: User, password: str) -> None:
        """Полное удаление: профиль, попытки, приглашения, отклики удаляются каскадно (ON DELETE CASCADE)."""
        if not verify_password(password, user.password_hash):
            raise Unauthorized("Неверный пароль", "INVALID_CREDENTIALS")
        self.db.add(AuthEvent(user_id=None, event="account_deleted"))  # факт удаления без ПДн
        self.db.execute(delete(User).where(User.id == user.id))
        self.db.commit()


__all__ = ["PrivacyService", "CandidateRepository"]
