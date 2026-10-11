from fastapi import APIRouter

from app import reference as ref

router = APIRouter(prefix="/reference", tags=["Справочники"])


@router.get("", summary="Все справочники одним запросом (кэшируйте на фронте)")
def all_reference():
    return {
        "grades": ref.GRADES, "specializations": ref.SPECIALIZATIONS, "industries": ref.INDUSTRIES,
        "work_formats": ref.WORK_FORMATS, "team_roles": ref.TEAM_ROLES, "skills": ref.SKILLS,
        "soft_skills": ref.SOFT_SKILLS, "survey": ref.SURVEY,
    }
