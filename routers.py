import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from gigachat import GigaChat

import config
from config import GIGA_TOKEN

# 3. Принудительно читаем именно этот файл

router = APIRouter()
# ... дальше твой остальной код без изменений

# 3. Схема данных, которые мы ждем от фронтенда (React)
class ResumeRequest(BaseModel):
    resume_text: str


# 4. Основной эндпоинт для парсинга
@router.post("/api/cv/parse")
def parse_resume(request: ResumeRequest):
    token = config.GIGA_TOKEN
    if not token:
        # Если ключа нет, сразу отдаем понятную ошибку фронтенду
        raise HTTPException(status_code=500, detail="Ошибка сервера: Токен GigaChat не найден в .env")

    # Жесткий системный промпт с указанием полей для JSON
    system_prompt = (
        "Ты — ИТ-рекрутер. Извлеки информацию из резюме. "
        "Ответ верни строго в формате JSON. "
        "Обязательные ключи: 'full_name', 'grade', 'tech_stack' (массив строк), 'experience_years'."
    )

    # Динамически подставляем текст, который прислал фронтенд
    user_prompt = f"Текст резюме кандидата:\n{request.resume_text}"

    try:
        # Используем модель GigaChat (или GigaChat-Max, если есть доступ)
        with GigaChat(credentials=token, verify_ssl_certs=False, model="GigaChat-2") as giga:
            response = giga.chat({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1  # Минимум фантазии, только факты
            })

            # Возвращаем JSON-ответ на фронтенд
            return {
                "status": "success",
                "extracted_data": response.choices[0].message.content
            }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка API GigaChat: {e}")


# ==========================================
# БЛОК ДЛЯ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ
# (Запустите этот файл напрямую, чтобы проверить работу без запуска всего сервера)
# ==========================================
if __name__ == "__main__":
    print("⏳ Отправляем тестовый запрос в GigaChat...\n")

    # Имитируем запрос от фронтенда
    test_request = ResumeRequest(
        resume_text="Меня зовут Алексей Иванов. Я работаю Backend-разработчиком 3 года. Пишу на Python, использую FastAPI, Docker и PostgreSQL. Претендую на позицию Middle."
    )

    try:
        result = parse_resume(test_request)
        print("✅ УСПЕХ! Ответ нейросети:\n")
        print(result["extracted_data"])
    except Exception as err:
        print(f"❌ ОШИБКА: {err}")