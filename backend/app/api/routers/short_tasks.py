from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_candidate, current_employer
from app.core.errors import errors
from app.models import CandidateProfile, EmployerProfile
from app.schemas.short_task import ShortTaskCreate, ShortTaskOut, SubmissionCreate, SubmissionOut, SubmissionReview
from app.services.short_task_service import ShortTaskService

router = APIRouter(prefix="/short-tasks", tags=["Короткие задания"], responses=errors(401, 403))


@router.post("", response_model=ShortTaskOut, status_code=status.HTTP_201_CREATED, summary="Работодатель: создать задание")
def create(data: ShortTaskCreate, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return ShortTaskService(db).create(e, data)


@router.get("/mine", response_model=list[ShortTaskOut], summary="Работодатель: мои задания")
def mine(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return ShortTaskService(db).mine(e)


@router.post("/{task_id}/close", response_model=ShortTaskOut, responses=errors(404), summary="Работодатель: закрыть")
def close(task_id: int, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return ShortTaskService(db).close(e, task_id)


@router.get("/feed", response_model=list[ShortTaskOut], summary="Кандидат: задания для моей категории")
def feed(c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return ShortTaskService(db).feed(c)


@router.post("/{task_id}/submit", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED,
             responses=errors(400, 404, 409), summary="Кандидат: отправить решение или подход")
def submit(task_id: int, data: SubmissionCreate, c: CandidateProfile = Depends(current_candidate),
           db: Session = Depends(get_db)):
    return ShortTaskService(db).submit(c, task_id, data.answer)


@router.get("/{task_id}/submissions", response_model=list[SubmissionOut], responses=errors(404),
            summary="Работодатель: решения по заданию")
def submissions(task_id: int, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return ShortTaskService(db).submissions(e, task_id)


@router.post("/submissions/{submission_id}/review", response_model=SubmissionOut, responses=errors(404),
             summary="Работодатель: оценить решение (0..10)")
def review(submission_id: int, data: SubmissionReview, e: EmployerProfile = Depends(current_employer),
           db: Session = Depends(get_db)):
    return ShortTaskService(db).review(e, submission_id, data)
