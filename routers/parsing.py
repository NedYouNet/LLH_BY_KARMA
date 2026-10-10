import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from data_science.resume_parser import parse_resume

router = APIRouter(prefix="/api", tags=["Parsing"])


# Убрали async: теперь FastAPI сам отправит эту тяжелую функцию в отдельный поток,
# и Tesseract не заблокирует сервер для других пользователей.
@router.post("/parse-cv")
def parse_cv(file: UploadFile = File(...)):
    # Проверка расширения с учетом регистра (например, для .PDF)
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Только PDF файлы разрешены")

    # Создаем временный файл для сохранения загруженного PDF
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")

    try:
        # Записываем байты из запроса во временный файл синхронно
        with os.fdopen(fd, 'wb') as f:
            f.write(file.file.read())

        # Вызываем функцию парсинга из resume_parser.py
        parsed_data = parse_resume(temp_path)

        return {
            "status": "success",
            "profile": parsed_data
        }
    except Exception as e:
        # Прячем внутреннюю ошибку от пользователя, чтобы не раскрывать детали реализации,
        # в рабочей версии ошибку `e` нужно писать в лог.
        raise HTTPException(status_code=500, detail="Ошибка при обработке документа")
    finally:
        # Обязательно удаляем временный файл, чтобы не засорять сервер
        if os.path.exists(temp_path):
            os.remove(temp_path)