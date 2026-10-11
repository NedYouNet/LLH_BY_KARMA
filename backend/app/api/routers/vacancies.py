from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_candidate, current_employer, current_user
from app.core.errors import errors
from app.models import CandidateProfile, EmployerProfile, User
from app.repositories.repos import CandidateRepository, EmployerRepository
from app.schemas.candidate import Grade, Spec, WorkFormat
from app.schemas.common import Page
from app.schemas.matching import SearchOut
from app.schemas.testing import AssessmentPreview
from app.schemas.vacancy import (
    ApplicationCreate, ApplicationOut, ApplicationStatusUpdate, VacancyCreate, VacancyOut, VacancyUpdate,
)
from app.services.matching_service import MatchingService
from app.services.vacancy_service import VacancyService

router = APIRouter(tags=["Вакансии и отклики"], responses=errors(401, 403))


@router.get("/vacancies", response_model=Page[VacancyOut], summary="Лента вакансий (для кандидата и всех)")
def list_vacancies(specialization: Spec | None = None, grade: Grade | None = None,
                   q: str | None = Query(None, description="Поиск по названию и описанию"),
                   salary_min: int | None = Query(None, description="Показывать, где salary_to ≥ этого"),
                   work_format: WorkFormat | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    cand = CandidateRepository(db).by_user(user.id) if user.role == "candidate" else None
    total, items = VacancyService(db).list_public(cand, specialization=specialization, grade=grade, q=q,
                                                  salary_min=salary_min, work_format=work_format,
                                                  offset=(page - 1) * size, limit=size)
    return Page(total=total, items=items)


@router.post("/vacancies", response_model=VacancyOut, status_code=status.HTTP_201_CREATED,
             summary="Работодатель: опубликовать вакансию (= описать потребность)")
def create_vacancy(data: VacancyCreate, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return VacancyService(db).create(e, data)


@router.get("/vacancies/mine", response_model=list[VacancyOut], summary="Работодатель: мои вакансии")
def my_vacancies(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return VacancyService(db).list_mine(e)


@router.get("/vacancies/{vacancy_id}", response_model=VacancyOut, responses=errors(404), summary="Вакансия")
def get_vacancy(vacancy_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cand = CandidateRepository(db).by_user(user.id) if user.role == "candidate" else None
    return VacancyService(db).get_public(vacancy_id, cand)


@router.patch("/vacancies/{vacancy_id}", response_model=VacancyOut, responses=errors(400, 404),
              summary="Работодатель: редактировать / закрыть (status=closed)")
def update_vacancy(vacancy_id: int, data: VacancyUpdate, e: EmployerProfile = Depends(current_employer),
                   db: Session = Depends(get_db)):
    return VacancyService(db).update(e, vacancy_id, data)


@router.get("/vacancies/{vacancy_id}/matches", response_model=SearchOut, responses=errors(404),
            summary="Работодатель: подборка кандидатов под вакансию с обоснованием")
def vacancy_matches(vacancy_id: int, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                    e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    v = VacancyService(db).owned(e, vacancy_id)
    return MatchingService(db).for_vacancy(e, v, page, size)


@router.get("/vacancies/{vacancy_id}/assessment-preview", response_model=AssessmentPreview, responses=errors(404),
            summary="Как система сформирует тест под эту вакансию (2 разных варианта)")
def assessment_preview(vacancy_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    return VacancyService(db).assessment_preview(vacancy_id)


@router.post("/vacancies/{vacancy_id}/apply", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED,
             responses=errors(400, 404, 409), summary="Кандидат: откликнуться самому")
def apply(vacancy_id: int, data: ApplicationCreate | None = None, c: CandidateProfile = Depends(current_candidate),
          db: Session = Depends(get_db)):
    return VacancyService(db).apply(c, vacancy_id, data.cover_letter if data else None)


@router.get("/applications", response_model=list[ApplicationOut],
            summary="Отклики: кандидат — мои, работодатель — на мои вакансии (?vacancy_id=)")
def applications(vacancy_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    svc = VacancyService(db)
    if user.role == "candidate":
        return svc.my_applications(CandidateRepository(db).by_user(user.id))
    return svc.employer_applications(EmployerRepository(db).by_user(user.id), vacancy_id)


@router.patch("/applications/{application_id}", response_model=ApplicationOut, responses=errors(404, 409),
              summary="Работодатель: просмотрено / принять / отклонить отклик")
def set_application_status(application_id: int, data: ApplicationStatusUpdate,
                           e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return VacancyService(db).set_status(e, application_id, data)


@router.post("/applications/{application_id}/withdraw", response_model=ApplicationOut, responses=errors(404, 409),
             summary="Кандидат: отозвать отклик")
def withdraw_application(application_id: int, c: CandidateProfile = Depends(current_candidate),
                         db: Session = Depends(get_db)):
    return VacancyService(db).withdraw(c, application_id)
