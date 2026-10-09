import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from gigachat import GigaChat

import config
from prompts import get_matching_system_prompt

router = APIRouter()


class MatchRequest(BaseModel):
    candidate_profile: str  # Спарсенные данные кандидата (можно JSON-строкой)
    vacancy_text: str  # Описание вакансии


class MatchResponse(BaseModel):
    match_percentage: int
    explanation: str
    pros: list
    cons: list


@router.post("/api/match", response_model=MatchResponse)
def match_candidate_and_vacancy(request: MatchRequest):
    token = config.GIGA_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="Ключ GigaChat не настроен в config.py")

    user_prompt = f"""
    Вакансия:
    {request.vacancy_text}

    Профиль кандидата:
    {request.candidate_profile}
    """

    try:
        # Используем GigaChat-Pro с низкой температурой для аналитики
        with GigaChat(credentials=token, verify_ssl_certs=False, model="GigaChat-Pro") as giga:
            response = giga.chat({
                "messages": [
                    {"role": "system", "content": get_matching_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2  # Низкая температура = меньше фантазий, больше фактов
            })

            raw_response = response.choices[0].message.content
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            ai_data = json.loads(clean_json)

            return MatchResponse(
                match_percentage=ai_data.get("match_percentage", 0),
                explanation=ai_data.get("explanation", "Не удалось сформировать объяснение."),
                pros=ai_data.get("pros", []),
                cons=ai_data.get("cons", [])
            )

    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Ошибка LLM: получен невалидный JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")