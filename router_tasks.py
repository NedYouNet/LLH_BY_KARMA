import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from gigachat import GigaChat

# Импортируем ваши локальные файлы
from invariants import TASK_INVARIANTS
from prompts import get_masking_system_prompt
import config  # Убедитесь, что ваш файл с ключом называется config.py

router = APIRouter()

# Схема для ответа API (контракт с фронтендом)
class GeneratedTaskResponse(BaseModel):
    task_id: str
    difficulty: str
    title: str
    description: str
    input_format: str
    output_format: str

@router.get("/api/tasks/generate", response_model=GeneratedTaskResponse)
def generate_unique_task(task_id: str, theme: str = "IT-инфраструктура"):
    """
    Генерирует уникальную формулировку задачи на основе инварианта.
    """
    # 1. Ищем математическое ядро задачи
    invariant = TASK_INVARIANTS.get(task_id)
    if not invariant:
        raise HTTPException(status_code=404, detail="Инвариант задачи не найден")

    # 2. Берем токен из файла config.py
    token = config.GIGA_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="Ключ GigaChat не настроен в config.py")

    # 3. Формируем запрос для нейросети
    user_prompt = f"""
    Тематика: {theme}
    Суть алгоритма: {invariant['math_core']}
    Вход: {invariant['inputs']}
    Вывод: {invariant['outputs']}
    Сгенерируй JSON.
    """

    try:
        # 4. Отправляем запрос к LLM (ОБЯЗАТЕЛЬНО указана модель GigaChat-Pro)
        with GigaChat(credentials=token, verify_ssl_certs=False, model="GigaChat-2") as giga:
            response = giga.chat({
                "messages": [
                    {"role": "system", "content": get_masking_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.8  # Высокая температура для разнообразия легенд
            })

            raw_response = response.choices[0].message.content

            # Очистка ответа от возможных markdown-тегов (```json ... ```)
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()

            # Парсим JSON от нейросети
            ai_data = json.loads(clean_json)

            # 5. Возвращаем структурированный ответ
            return GeneratedTaskResponse(
                task_id=task_id,
                difficulty=invariant["difficulty"],
                title=ai_data["title"],
                description=ai_data["description"],
                input_format=ai_data["input_format"],
                output_format=ai_data["output_format"]
            )

    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Нейросеть вернула невалидный JSON. Попробуйте еще раз.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {e}")