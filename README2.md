# Бэкенд-микросервис: Парсинг и Мэтчинг кандидатов (ФСП)

В этом репозитории реализована Data Science и базовая Backend-часть платформы для хакатона ФСП. Мы используем FastAPI для создания API, `pandas` для эффективной обработки данных, алгоритмы умного ранжирования и OCR-парсинг PDF-резюме.

## 🗂 Структура проекта

* `main.py` — Точка входа в приложение FastAPI (включает настройку CORS и подключение роутеров).
* `routers/` — Логическое разделение API:
  * `matching.py` — Эндпоинт `/api/matching/` для выдачи отранжированных кандидатов.
  * `parsing.py` — Эндпоинт `/api/parse-cv` для приема PDF и возврата JSON-профиля.
* `data_science/` — Ядро бизнес-логики:
  * `matcher.py` — Алгоритм ранжирования с весами (тесты, ФСП, скиллы, профиль).
  * `resume_parser.py` — Извлечение сущностей из PDF (PyMuPDF + Tesseract OCR).
  * `synthetic_data.py` — Скрипт генерации фейковых кандидатов для демо-базы.
  * `models.py` — Pydantic-модели (контракты данных для API).
  * `validation.py` — Скрипт для расчета метрики Precision@10.

## 🛠 Установка и локальный запуск

**Шаг 1. Системные зависимости**
Для корректной работы парсера резюме (`resume_parser.py`) в системе должен быть установлен **Tesseract OCR**.
* Windows: Скачать инсталлятор с GitHub (tesseract-ocr).
* macOS: `brew install tesseract`
* Linux: `sudo apt install tesseract-ocr tesseract-ocr-rus`

**Шаг 2. Виртуальное окружение и библиотеки**
```bash
python -m venv .venv
source .venv/bin/activate  # Для Windows: .venv\Scripts\activate
pip install fastapi uvicorn pandas pydantic pymupdf pytesseract Pillow faker
```

**Шаг 3. Генерация синтетической базы**
Прежде чем запускать сервер, необходимо сгенерировать датасет кандидатов (иначе мэтчеру не с чем будет работать).
```bash
python -m data_science.synthetic_data
```
*Файл `candidates.csv` появится в папке `data_science/data/`.*

**Шаг 4. Запуск сервера**
```bash
uvicorn main:app --reload
```
API будет доступно по адресу: `http://127.0.0.1:8000`
Интерактивная документация (Swagger): `http://127.0.0.1:8000/docs`

## 🚀 Доступные эндпоинты

Вся документация и форматы запросов/ответов автоматически генерируются в Swagger (`/docs`).
* `GET /` — Healthcheck сервера.
* `POST /api/parse-cv` — Принимает файл (form-data, key="file"). Возвращает JSON с ФИО, контактами, скиллами и опытом работы.
* `POST /api/matching/` — Принимает JSON вакансии (специализация, грейд, стек). Возвращает анонимный топ кандидатов с подробным расчетом скора (почему именно они в топе).
