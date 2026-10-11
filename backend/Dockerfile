# Образ бэкенда. Сборка: docker build -t fsp-backend ./backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Шрифт с кириллицей для генерации PDF-профиля
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала только зависимости — этот слой кэшируется и не пересобирается при правке кода
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Не запускаем приложение от root
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
# При старте: применяем миграции, затем запускаем сервер
# Число процессов: WEB_CONCURRENCY (по умолчанию 4; на стенде жюри с 8 CPU можно 8)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-4}"]
