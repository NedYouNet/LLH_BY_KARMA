from fastapi import APIRouter

from app.core.errors import NotFound, errors
from app.services import fsp_service

router = APIRouter(prefix="/fsp", tags=["ФСП (реестр достижений)"])


@router.get("/registry/{fsp_id}", responses=errors(404),
            summary="Что знает реестр ФСП об участнике: реальные результаты из таблицы или демо-данные")
def registry(fsp_id: str):
    """
    Сначала ищем ID в таблице реальных результатов (`verification_status: verified`, есть `source_url`).
    Если там нет — в демо-реестре (`verification_status: demo`): 6 цифр; оканчивается на 0 — участник
    без соревнований; иначе 1–5 достижений, одни и те же для одного ID.
    """
    data = fsp_service.registry.get_participant(fsp_id)
    if data is None:
        raise NotFound("Участник не найден", "FSP_NOT_FOUND")
    return {**data, "fsp_score": fsp_service.compute_fsp_score(data["achievements"])}
