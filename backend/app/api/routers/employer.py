"""Работодатель: профиль компании, поиск кандидатов, карточка кандидата, избранное."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_employer
from app.core.errors import NotFound, errors
from app.models import EmployerProfile, Vacancy
from app.schemas.candidate import CandidateDetail, Grade, Spec
from app.schemas.employer import AtsConfigIn, AtsConfigOut, AtsDeliveryOut, EmployerProfileOut, EmployerProfileUpdate
from app.schemas.matching import CategoryBucket, NeedIn, NeedOut, SearchIn, SearchOut, ShortlistIn, ShortlistOut
from app.services.ats_service import AtsService
from app.services.matching_service import MatchingService

router = APIRouter(tags=["Работодатель: подбор"], responses=errors(401, 403))


@router.get("/employer/profile", response_model=EmployerProfileOut, summary="Профиль компании")
def get_profile(e: EmployerProfile = Depends(current_employer)):
    return e


@router.patch("/employer/profile", response_model=EmployerProfileOut, summary="Обновить профиль компании")
def update_profile(data: EmployerProfileUpdate, e: EmployerProfile = Depends(current_employer),
                   db: Session = Depends(get_db)):
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(e, k, v)
    if e.inn and e.trust_level == "unverified":
        e.trust_level = "inn_provided"  # задел: тут будет проверка через API ФНС
    db.commit()
    return e


# ----------------------------- потребности -----------------------------
@router.get("/employer/needs", response_model=list[NeedOut], summary="Мои сохранённые потребности («кого ищем»)")
def list_needs(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return MatchingService(db).list_needs(e)


@router.post("/employer/needs", response_model=NeedOut, status_code=status.HTTP_201_CREATED,
             summary="Сохранить новую потребность")
def create_need(data: NeedIn, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return MatchingService(db).create_need(e, data)


@router.get("/employer/needs/{need_id}", response_model=NeedOut, responses=errors(404), summary="Одна потребность")
def get_need(need_id: int, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return NeedOut.model_validate(MatchingService(db).get_need(e, need_id), from_attributes=True)


@router.put("/employer/needs/{need_id}", response_model=NeedOut, responses=errors(404),
            summary="Изменить потребность (присылается целиком)")
def update_need(need_id: int, data: NeedIn, e: EmployerProfile = Depends(current_employer),
                db: Session = Depends(get_db)):
    return MatchingService(db).update_need(e, need_id, data)


@router.delete("/employer/needs/{need_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404),
               summary="Удалить потребность")
def delete_need(need_id: int, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    MatchingService(db).delete_need(e, need_id)


def _split(values: list[str]) -> list[str]:
    """Поддерживаем и ?stack=Python&stack=Docker, и ?stack=Python,Docker."""
    out: list[str] = []
    for v in values:
        for part in v.split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


@router.get("/candidates", response_model=SearchOut,
            summary="Подборка через параметры адреса (удобно для фильтров на фронте)")
def candidates(needs_id: int | None = Query(None, description="Взять критерии из сохранённой потребности"),
               specialization: Spec | None = None,
               grade: list[Grade] = Query([], description="Можно несколько: ?grade=junior&grade=middle"),
               stack: list[str] = Query([], description="?stack=Python,Docker или ?stack=Python&stack=Docker"),
               only_fsp: bool = Query(False, description="Только с достижениями ФСП"),
               only_verified: bool = Query(False, description="Только с грейдом, подтверждённым тестом"),
               min_test_score: float | None = Query(None, ge=0, le=100),
               text: str | None = Query(None, max_length=2000, description="Описание потребности свободным текстом"),
               page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    """То же, что POST /candidates/search, но фильтры — в адресе. Пустая выдача: `items: [], total: 0`."""
    return MatchingService(db).search_query(e, needs_id=needs_id, specialization=specialization, grades=list(grade),
                                            stack=_split(stack), only_fsp=only_fsp, min_test_score=min_test_score,
                                            text=text, page=page, page_size=page_size, only_verified=only_verified)


@router.get("/candidates/categories", response_model=list[CategoryBucket],
            summary="Обзор банка: категории и сколько в них кандидатов")
def categories(_: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return MatchingService(db).categories_overview()


@router.post("/candidates/search", response_model=SearchOut,
             summary="Подборка: фильтры + ранжирование + обоснование каждого кандидата")
def search(req: SearchIn, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    """
    Выдача строится по КАТЕГОРИЯМ, присвоенным тестом (а не по тексту резюме).
    В каждой карточке: `match_score` (0..100), `reasons` (плашки «почему он»), `breakdown` (вклад компонент).
    Контакты (`contacts`) = null, пока кандидат не принял приглашение или не откликнулся сам.
    """
    return MatchingService(db).search(e, req)


@router.get("/candidates/{candidate_id}", response_model=CandidateDetail, responses=errors(404),
            summary="Карточка кандидата (контакты — только после принятия инвайта/отклика)")
def candidate(candidate_id: int, vacancy_id: int | None = Query(None, description="Посчитать соответствие этой вакансии"),
              e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    vacancy = None
    if vacancy_id:
        vacancy = db.get(Vacancy, vacancy_id)
        if not vacancy or vacancy.employer_id != e.id:
            raise NotFound("Вакансия не найдена")
    return MatchingService(db).candidate_for_employer(e, candidate_id, vacancy)


@router.get("/shortlist", response_model=list[ShortlistOut], summary="Избранные кандидаты")
def shortlist(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return MatchingService(db).shortlist(e)


@router.post("/shortlist", response_model=ShortlistOut, status_code=status.HTTP_201_CREATED, responses=errors(404, 409),
             summary="Добавить в избранное")
def add_shortlist(data: ShortlistIn, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return MatchingService(db).add_to_shortlist(e, data)


@router.delete("/shortlist/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404),
               summary="Убрать из избранного")
def remove_shortlist(candidate_id: int, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    MatchingService(db).remove_from_shortlist(e, candidate_id)


# ----------------------------------------------------------- интеграция с ATS
ats_router = APIRouter(tags=["Работодатель: интеграция с ATS"], responses=errors(401, 403))


@ats_router.get("/employer/integrations/ats", response_model=AtsConfigOut,
            summary="Настройки отправки кандидатов в вашу ATS и последние отправки")
def ats_config(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return AtsService(db).config(e)


@ats_router.put("/employer/integrations/ats", response_model=AtsConfigOut, responses=errors(400, 422),
            summary="Подключить ATS: адрес вебхука (секрет выдаётся один раз)")
def ats_configure(data: AtsConfigIn, e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    """
    Когда кандидат примет ваше приглашение, в ATS придёт POST с событием `invitation.accepted` и карточкой
    кандидата. Проверяйте подпись: `X-FSP-Signature = sha256=HMAC_SHA256(secret, X-FSP-Timestamp + "." + тело)`.

    Нет своей ATS? На демо-стенде есть встроенный тестовый приёмник:
    `http://localhost:8000/api/mock-ats/webhook`, полученные события — `GET /api/mock-ats/events`.
    """
    return AtsService(db).configure(e, data.webhook_url, data.rotate_secret)


@ats_router.post("/employer/integrations/ats/test", response_model=AtsDeliveryOut, responses=errors(404),
             summary="Отправить в ATS тестовое событие")
def ats_test(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    return AtsService(db).send_test(e)


@ats_router.delete("/employer/integrations/ats", status_code=status.HTTP_204_NO_CONTENT,
               summary="Отключить интеграцию с ATS")
def ats_disable(e: EmployerProfile = Depends(current_employer), db: Session = Depends(get_db)):
    AtsService(db).disable(e)
