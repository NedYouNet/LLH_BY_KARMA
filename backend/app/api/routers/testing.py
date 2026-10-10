from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_candidate
from app.core.errors import errors
from app.models import CandidateProfile
from app.schemas.testing import AttemptOut, AttemptResultOut, AttemptSummary, StartAttemptIn, SubmitIn
from app.services.testing_service import TestingService

router = APIRouter(prefix="/testing", tags=["Кандидат: тестирование"], responses=errors(401, 403))


@router.post("/attempts", response_model=AttemptOut, status_code=status.HTTP_201_CREATED, responses=errors(404, 409),
             summary="Шаг 2–3: выбрать грейд и начать тест")
def start(data: StartAttemptIn, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    """
    Генерирует УНИКАЛЬНЫЙ вариант теста. Ошибки 409 (поле `code`):
    SURVEY_REQUIRED, ATTEMPT_IN_PROGRESS (+attempt_id), GRADE_COOLDOWN (+next_change_at), RETRY_COOLDOWN.
    """
    return TestingService(db).start(c, data.specialization, data.target_grade, data.vacancy_id)


@router.get("/attempts", response_model=list[AttemptSummary], summary="История моих попыток")
def history(c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    return TestingService(db).history(c)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut, responses=errors(404),
            summary="Получить попытку (например, после перезагрузки страницы)")
def get_attempt(attempt_id: int, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    svc = TestingService(db)
    return svc.attempt_out(svc.get_owned(c, attempt_id))


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultOut, responses=errors(400, 404, 409),
             summary="Отправить ответы и получить результат + решение по грейду")
def submit(attempt_id: int, data: SubmitIn, c: CandidateProfile = Depends(current_candidate),
           db: Session = Depends(get_db)):
    return TestingService(db).submit(c, attempt_id, data.answers)


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResultOut, responses=errors(404, 409),
            summary="Результат завершённой попытки")
def result(attempt_id: int, c: CandidateProfile = Depends(current_candidate), db: Session = Depends(get_db)):
    svc = TestingService(db)
    return svc.result_out(svc.get_owned(c, attempt_id))
