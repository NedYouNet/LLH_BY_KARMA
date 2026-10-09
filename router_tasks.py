import json
import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from gigachat import GigaChat

from invariants import TASK_INVARIANTS
from prompts import get_masking_system_prompt
import config

router = APIRouter()


# 1. Новые схемы данных
class TaskItem(BaseModel):
    task_id: str
    difficulty: str
    title: str
    description: str
    input_format: str
    output_format: str
    public_tests: list


class TournamentSetResponse(BaseModel):
    theme: str
    tasks: List[TaskItem]


# 2. Новый эндпоинт генерации сета задач
@router.get("/api/tasks/generate-tournament", response_model=TournamentSetResponse)
def generate_tournament_set(theme: str = "IT-инфраструктура"):
    """
    Создает сбалансированный турнирный пакет (Junior, Middle, Senior) в единой тематике.
    """
    token = config.GIGA_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="Ключ GigaChat не настроен в config.py")

    # Группируем задачи по сложности
    juniors = [k for k, v in TASK_INVARIANTS.items() if v["difficulty"] == "Junior"]
    middles = [k for k, v in TASK_INVARIANTS.items() if v["difficulty"] == "Middle"]
    seniors = [k for k, v in TASK_INVARIANTS.items() if v["difficulty"] == "Senior"]

    # Проверяем, что в базе есть хотя бы по одной задаче каждого грейда
    if not (juniors and middles and seniors):
        raise HTTPException(status_code=500,
                            detail="Недостаточно задач в базе для формирования сета (нужны Junior, Middle и Senior).")

    # Случайно выбираем по одной задаче каждого грейда
    selected_task_ids = [
        random.choice(juniors),
        random.choice(middles),
        random.choice(seniors)
    ]

    generated_tasks = []

    # Открываем ОДНУ сессию с GigaChat и гоняем задачи по очереди
    try:
        with GigaChat(credentials=token, verify_ssl_certs=False, model="GigaChat-2") as giga:

            for t_id in selected_task_ids:
                invariant = TASK_INVARIANTS[t_id]

                user_prompt = f"""
                Тематика (общий сеттинг): {theme}
                Сложность: {invariant['difficulty']}
                Суть алгоритма: {invariant['math_core']}
                Вход: {invariant['inputs']}
                Вывод: {invariant['outputs']}
                Сгенерируй JSON.
                """

                response = giga.chat({
                    "messages": [
                        {"role": "system", "content": get_masking_system_prompt()},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.8
                })

                raw_response = response.choices[0].message.content
                clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                # ... парсинг ответа от GigaChat ...
                ai_data = json.loads(clean_json)

                # Собираем готовую задачу
                generated_tasks.append(
                    TaskItem(
                        task_id=t_id,
                        difficulty=invariant["difficulty"],
                        title=ai_data.get("title", "Без названия"),
                        description=ai_data.get("description", ""),
                        input_format=ai_data.get("input_format", ""),
                        output_format=ai_data.get("output_format", ""),
                        # Подтягиваем публичные тесты напрямую из базы
                        public_tests=invariant.get("public_tests", [])
                    )
                )

        # Возвращаем турнирный пак фронтенду
        return TournamentSetResponse(
            theme=theme,
            tasks=generated_tasks
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Нейросеть вернула невалидный JSON. Повторите запрос.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка API: {e}")