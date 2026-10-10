"""
Разбор PDF-резюме — место для ML-модели (участник 3).

КОНТРАКТ (бэкенд вызывает так):
    parse_resume(pdf_bytes, text, filename) -> dict | None

  pdf_bytes — исходный файл (до 5 МБ, уже проверено, что это PDF);
  text      — текст, который бэкенд уже извлёк из PDF (pypdf); можно использовать его, чтобы не парсить заново;
  filename  — имя файла.

  Вернуть словарь с любыми из полей (лишние ключи игнорируются):
    full_name: str, email: str, phone: str, telegram: str, city: str,
    skills: list[str], soft_skills: list[str], team_roles: list[str],
    experience_years: float, specialization_guess: "backend"|"frontend"|"data_science"|"qa"|"devops",
    grade_guess: "intern"|"junior"|"middle"|"senior", about: str
  Вернуть None — «не смог»: бэкенд возьмёт встроенный парсер. Исключения тоже перехватываются.

ПРАВИЛА: без видеокарты; укладываться в ML_TIMEOUT_SECONDS (20 с); если нужен внешний LLM — только российский
(GigaChat, YandexGPT…: в резюме персональные данные), ключ — из переменной окружения, не в коде;
описать модель и зачем она в docs/11_ml.md (требование организаторов).
"""

ENABLED = False  # поставить True, когда parse_resume реализована


def parse_resume(pdf_bytes: bytes, text: str, filename: str) -> dict | None:
    return None
