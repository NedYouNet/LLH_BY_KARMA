import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from data_science.resume_parser import parse_resume

router = APIRouter(prefix="/api", tags=["Parsing"])


@router.post("/parse-cv")
async def parse_cv(file: UploadFile = File(...)):
    # Проверяем, что загружен именно PDF
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Только PDF файлы разрешены")

    # Создаем временный файл для сохранения загруженного PDF
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")

    try:
        # Записываем байты из запроса во временный файл
        with os.fdopen(fd, 'wb') as f:
            f.write(await file.read())

        # Вызываем твою функцию парсинга из resume_parser.py
        parsed_data = parse_resume(temp_path)

        return {
            "status": "success",
            "profile": parsed_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Обязательно удаляем временный файл, чтобы не засорять сервер
        if os.path.exists(temp_path):
            os.remove(temp_path)