# Базовый образ Python
FROM python:3.9-slim

# Создаем пользователя без прав root для безопасности (Критично для песочницы!)
RUN useradd -m sandboxuser

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Меняем владельца файлов и переключаемся на безопасного пользователя
RUN chown -R sandboxuser:sandboxuser /app
USER sandboxuser

# Открываем порт для FastAPI
EXPOSE 8000

# Запуск микросервиса
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]