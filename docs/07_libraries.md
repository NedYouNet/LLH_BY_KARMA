# Зависимости

Python 3.12; полный фиксированный список — `backend/requirements.txt`, зависимости проверок — `requirements-dev.txt`. Основные: FastAPI 0.115.12, Uvicorn 0.34.2, SQLAlchemy 2.0.41, Alembic 1.16.1, psycopg 3.2.9, Pydantic 2.11.5, httpx 0.28.1, pypdf 5.6.0, ReportLab 4.4.1, openpyxl 3.1.5, cryptography 45.0.5, GigaChat SDK 0.2.3. pytest 8.3.5 — только для проверок.

Frontend: Node.js 22 в Docker, React 19, Vite 8, Tailwind CSS 4, Monaco Editor через `@monaco-editor/react`. Диапазоны — в `frontend/package.json`, точные версии — в `frontend/package-lock.json`; установка через `npm ci`.

Контейнеры: PostgreSQL 16 Alpine, nginx 1.27 Alpine, Mailpit. Mailpit использует тег latest и поэтому не фиксирует точный образ; для воспроизводимого промышленного развёртывания нужно закрепить digest. GPU и отдельный ML-сервер для текущей сборки не требуются.

Tesseract, PyMuPDF и отдельные зависимости CSV-прототипа участника 4 в основной сборке не установлены: OCR оттуда не подключён.
