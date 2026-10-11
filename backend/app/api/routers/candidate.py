"""Личный кабинет кандидата (всё про «меня»): /api/candidate/..."""
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_candidate
from app.core.errors import errors
from app.models import CandidateProfile
from app.schemas.candidate import (
    CandidateProfileOut, CandidateProfileUpdate, CategoryStatus, Consents, FspLinkIn, Privacy, ResumeParseOut,
    SurveyIn,
)
from app.services.candidate_service import CandidateService, profile_out
from app.services.pdf_service import build_profile_pdf
from app.services.privacy_service import PrivacyService
from app.services.testing_service import TestingService

router = APIRouter(prefix="/candidate", tags=["Кандидат: профиль"], responses=errors(401, 403))


@router.get("/profile", response_model=CandidateProfileOut, summary="Мой профиль")
def get_profile(c: CandidateProfile = Depends(current_candidate)):
    return profile_out(c)


@router.patch("/profile", response_model=CandidateProfileOut, summary="Обновить профиль (только присланные поля)")
def update_profile(data: CandidateProfileUpdate, c: CandidateProfile = Depends(current_candidate),
                   db: Session = Depends(get_db)):
    return profile_out(CandidateService(db).update_profile(c, data))


@router.post("/resume/parse", response_model=ResumeParseOut, responses=errors(400),
             summary="Загрузить PDF-резюме и распознать поля")
async def parse_resume(file: UploadFile = File(..., description="PDF до 5 МБ"),
                       apply: bool = Query(True, description="Сразу заполнить пустые поля профиля"),
                       c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    """Сначала ML (app/ml или ML-сервис по ML_SERVICE_URL), при недоступности — встроенный парсер. Фронт показывает лоадер."""
    content = await file.read()
    return CandidateService(db).parse_resume(c, content, file.filename or "resume.pdf", apply)


@router.get("/profile/pdf", summary="Скачать стандартизированный PDF-профиль",
            response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def profile_pdf(c: CandidateProfile = Depends(current_candidate)):
    pdf = build_profile_pdf(c, c.user.email)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="profile_{c.id}.pdf"'})


@router.post("/survey", response_model=CandidateProfileOut, responses=errors(422),
             summary="Шаг 1: анкета — IT-направление и грейд, на который претендую")
def survey(data: SurveyIn, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return profile_out(CandidateService(db).submit_survey(c, data))


@router.get("/category", response_model=CategoryStatus,
            summary="Моя категория, грейд, когда можно менять, на какие грейды можно пройти тест")
def category(c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return TestingService(db).status(c)


@router.put("/consents", response_model=CandidateProfileOut, responses=errors(400), summary="Согласия (152-ФЗ)")
def consents(data: Consents, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return profile_out(CandidateService(db).set_consents(c, data))


@router.put("/privacy", response_model=CandidateProfileOut, summary="Что видно работодателю")
def privacy(data: Privacy, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return profile_out(CandidateService(db).set_privacy(c, data))


@router.post("/fsp", response_model=CandidateProfileOut, responses=errors(404, 409),
             summary="Привязать ФСП ID и подтянуть достижения из реестра")
def link_fsp(data: FspLinkIn, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return profile_out(CandidateService(db).link_fsp(c, data.fsp_id))


@router.delete("/fsp", response_model=CandidateProfileOut, summary="Отвязать ФСП ID")
def unlink_fsp(c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return profile_out(CandidateService(db).unlink_fsp(c))


# ----------------------------- права по 152-ФЗ -----------------------------
class DeleteAccountIn(BaseModel):
    password: str


@router.get("/contact-access-log", summary="Кто и когда получил доступ к моим контактам")
def contact_access_log(c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    """Каждое раскрытие контактов работодателю записывается: компания, основание (инвайт/отклик), время."""
    return PrivacyService(db).contact_access_log(c)


@router.get("/export", summary="Выгрузить все мои данные (JSON)")
def export_data(c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    """Право субъекта ПДн знать, какие данные о нём обрабатываются (152-ФЗ, ст. 14)."""
    return PrivacyService(db).export(c)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT, responses=errors(401),
               summary="Удалить аккаунт и все мои данные")
def delete_account(data: DeleteAccountIn, c: CandidateProfile = Depends(current_candidate),
                   db: Session = Depends(get_db)):
    """Отзыв согласия + удаление (152-ФЗ, ст. 21). Требует пароль. Действие необратимо."""
    PrivacyService(db).delete_account(c.user, data.password)
