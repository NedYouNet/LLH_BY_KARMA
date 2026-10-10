from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_candidate, current_employer, current_user
from app.core.errors import errors
from app.models import CandidateProfile, EmployerProfile, User
from app.repositories.repos import CandidateRepository, EmployerRepository
from app.schemas.invitation import (ContactAccessIn, InvitationAnswer, InvitationCreate, InvitationOut,
                                   InvitationRespond)
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["Приглашения (главная механика)"], responses=errors(401, 403))

StatusFilter = Literal["sent", "viewed", "accepted", "declined", "withdrawn"]


@router.post("", response_model=InvitationOut, status_code=status.HTTP_201_CREATED, responses=errors(404, 409, 422),
             summary="Работодатель: пригласить кандидата (вилка ЗП обязательна)")
def create(data: InvitationCreate, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return InvitationService(db).create(e, data)


@router.get("", response_model=list[InvitationOut],
            summary="Мои приглашения: работодатель — отправленные, кандидат — входящие")
def my_invitations(status_: StatusFilter | None = Query(None, alias="status"), user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    svc = InvitationService(db)
    if user.role == "candidate":
        return svc.list_for_candidate(CandidateRepository(db).by_user(user.id), status_)
    return svc.list_for_employer(EmployerRepository(db).by_user(user.id), status_)


@router.get("/{invitation_id}", response_model=InvitationOut, responses=errors(404),
            summary="Открыть приглашение (кандидату — автоматически статус viewed)")
def get_one(invitation_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    svc = InvitationService(db)
    if user.role == "candidate":
        return svc.get_for_candidate(CandidateRepository(db).by_user(user.id), invitation_id)
    return svc.get_for_employer(EmployerRepository(db).by_user(user.id), invitation_id)


@router.post("/{invitation_id}/accept", response_model=InvitationOut, responses=errors(404, 409),
             summary="Кандидат: принять — контакты станут видны работодателю")
def accept(invitation_id: int, background: BackgroundTasks, data: InvitationRespond | None = None,
           c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return InvitationService(db).respond(c, invitation_id, True, data.reply if data else None, background)


@router.post("/{invitation_id}/decline", response_model=InvitationOut, responses=errors(404, 409),
             summary="Кандидат: отклонить")
def decline(invitation_id: int, data: InvitationRespond | None = None,
            c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return InvitationService(db).respond(c, invitation_id, False, data.reply if data else None)


@router.patch("/{invitation_id}/answer", response_model=InvitationOut, responses=errors(404, 409),
              summary="Кандидат: ответить одним запросом (status = accepted | rejected)")
def answer(invitation_id: int, data: InvitationAnswer, background: BackgroundTasks,
           c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    """Повторный ответ на уже завершённое приглашение -> 409 INVALID_STATUS_TRANSITION."""
    return InvitationService(db).respond(c, invitation_id, data.status == "accepted", data.reply, background)


@router.post("/{invitation_id}/withdraw", response_model=InvitationOut, responses=errors(404, 409),
             summary="Работодатель: отозвать приглашение")
def withdraw(invitation_id: int, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return InvitationService(db).withdraw(e, invitation_id)


@router.put("/{invitation_id}/contact-access", response_model=InvitationOut, responses=errors(404, 409),
            summary="Кандидат: закрыть свои контакты от компании (или открыть снова) после принятия")
def contact_access(invitation_id: int, data: ContactAccessIn, c: CandidateProfile = Depends(current_candidate),
                   db: Session = Depends(get_db)):
    """`{"granted": false}` — работодатель больше не видит контакты и полное имя; `{"granted": true}` — снова видит."""
    return InvitationService(db).set_contact_access(c, invitation_id, data.granted)
