"""
Справочники платформы: отрасли, специализации, грейды, навыки.

ТЗ разрешает составить справочник самим «на основе общепринятых в ИТ понятий».
Держим его в коде (а не в БД): он меняется редко, а так его легко версионировать в git.
Фронтенд получает его через GET /api/reference.
"""

# Грейды упорядочены: индекс = «уровень». Это важно для сравнения «выше/ниже».
GRADES: list[dict] = [
    {"code": "intern", "name": "Intern", "title_ru": "Стажёр", "level": 0, "experience": "без опыта"},
    {"code": "junior", "name": "Junior", "title_ru": "Младший", "level": 1, "experience": "до 1–2 лет"},
    {"code": "middle", "name": "Middle", "title_ru": "Средний", "level": 2, "experience": "2–4 года"},
    {"code": "senior", "name": "Senior", "title_ru": "Старший", "level": 3, "experience": "4+ лет"},
]
GRADE_CODES = [g["code"] for g in GRADES]
GRADE_LEVEL = {g["code"]: g["level"] for g in GRADES}
GRADE_NAME = {g["code"]: g["name"] for g in GRADES}

SPECIALIZATIONS: list[dict] = [
    {"code": "backend", "name": "Бэкенд-разработка", "short": "Бэкенд", "stack_hint": "Python, Go, Java, SQL"},
    {"code": "frontend", "name": "Фронтенд-разработка", "short": "Фронтенд", "stack_hint": "JavaScript, TypeScript, React, Vue"},
    {"code": "data_science", "name": "Data Science / ML", "short": "Data Science", "stack_hint": "Python, pandas, sklearn, PyTorch"},
    {"code": "qa", "name": "Тестирование (QA)", "short": "QA", "stack_hint": "pytest, Selenium, Postman"},
    {"code": "devops", "name": "DevOps / SRE", "short": "DevOps", "stack_hint": "Linux, Docker, Kubernetes, CI/CD"},
]
SPEC_CODES = [s["code"] for s in SPECIALIZATIONS]
SPEC_NAME = {s["code"]: s["name"] for s in SPECIALIZATIONS}
SPEC_SHORT = {s["code"]: s["short"] for s in SPECIALIZATIONS}

INDUSTRIES: list[dict] = [
    {"code": "it", "name": "Информационные технологии"},
    {"code": "fintech", "name": "Финтех и банки"},
    {"code": "ecommerce", "name": "E-commerce и ритейл"},
    {"code": "gamedev", "name": "Геймдев"},
    {"code": "edtech", "name": "Образование"},
    {"code": "govtech", "name": "Госсектор"},
    {"code": "telecom", "name": "Телеком"},
    {"code": "medtech", "name": "Медицина"},
    {"code": "industry", "name": "Промышленность"},
    {"code": "other", "name": "Другое"},
]
INDUSTRY_CODES = [i["code"] for i in INDUSTRIES]

WORK_FORMATS = [
    {"code": "office", "name": "Офис"},
    {"code": "remote", "name": "Удалённо"},
    {"code": "hybrid", "name": "Гибрид"},
]
WORK_FORMAT_CODES = [w["code"] for w in WORK_FORMATS]

TEAM_ROLES = ["Разработчик", "Техлид", "Тимлид", "Архитектор", "Ментор", "Капитан команды на соревнованиях"]

# Словарь навыков по специализациям: используется в опросе, парсинге резюме и подборе.
SKILLS: dict[str, list[str]] = {
    "backend": ["Python", "FastAPI", "Django", "Flask", "Go", "Java", "Spring", "C#", ".NET", "Node.js",
                "PostgreSQL", "MySQL", "MongoDB", "Redis", "Kafka", "RabbitMQ", "Docker", "Kubernetes",
                "REST", "gRPC", "GraphQL", "SQL", "SQLAlchemy", "Celery", "Linux", "Git", "Алгоритмы"],
    "frontend": ["JavaScript", "TypeScript", "React", "Vue", "Angular", "Next.js", "Redux", "HTML", "CSS",
                 "TailwindCSS", "Webpack", "Vite", "Jest", "REST", "GraphQL", "Figma", "Git", "Алгоритмы"],
    "data_science": ["Python", "pandas", "NumPy", "scikit-learn", "PyTorch", "TensorFlow", "SQL", "Statistics",
                     "Matplotlib", "CatBoost", "LightGBM", "NLP", "Computer Vision", "Spark", "Airflow", "Git",
                     "Алгоритмы"],
    "qa": ["Python", "Java", "pytest", "Selenium", "Playwright", "Postman", "REST", "SQL", "Allure", "JMeter",
           "Test design", "CI/CD", "Git", "Linux", "Docker"],
    "devops": ["Linux", "Bash", "Docker", "Kubernetes", "Terraform", "Ansible", "CI/CD", "GitLab CI",
               "GitHub Actions", "Prometheus", "Grafana", "Nginx", "PostgreSQL", "Python", "Go", "AWS",
               "Yandex Cloud", "Git"],
}
ALL_SKILLS = sorted({s for lst in SKILLS.values() for s in lst}, key=str.lower)

SOFT_SKILLS = ["Командная работа", "Коммуникация", "Самостоятельность", "Ответственность",
               "Работа в условиях дедлайна", "Наставничество", "Лидерство", "Аналитическое мышление"]

# Вопросы опроса «по отрасли и специализации» (первый шаг обязательного пути кандидата).
# «Отрасль» в ТЗ = IT-направление (так уточнили организаторы), поэтому первый вопрос — направление,
# а сфера бизнеса (финтех, ритейл…) — необязательное пожелание кандидата.
SURVEY = [
    {"id": "specialization", "question": "Ваше IT-направление", "type": "single", "options": SPEC_CODES,
     "required": True},
    {"id": "declared_grade", "question": "На какой грейд вы претендуете? Тест подтвердит его", "type": "single",
     "options": GRADE_CODES, "required": True},
    {"id": "industry", "question": "Предпочитаемая сфера бизнеса (необязательно)", "type": "single",
     "options": INDUSTRY_CODES, "required": False},
    {"id": "experience_years", "question": "Сколько лет коммерческого опыта?", "type": "number", "required": False},
    {"id": "skills", "question": "Ваш основной стек", "type": "multi", "options_by": "specialization", "required": False},
    {"id": "team_roles", "question": "Роли в команде", "type": "multi", "options": TEAM_ROLES, "required": False},
    {"id": "work_format", "question": "Предпочитаемый формат работы", "type": "single", "options": WORK_FORMAT_CODES, "required": False},
]


def category_label(specialization: str | None, grade: str | None) -> str | None:
    """Категория = специализация + грейд. Например: «Бэкенд · Middle»."""
    if not specialization or not grade:
        return None
    return f"{SPEC_SHORT.get(specialization, specialization)} · {GRADE_NAME.get(grade, grade)}"


def normalize_skill(raw: str) -> str | None:
    """Приводит навык к написанию из справочника ('postgresql' -> 'PostgreSQL'). Неизвестные возвращает как есть."""
    raw = raw.strip()
    if not raw:
        return None
    for s in ALL_SKILLS:
        if s.lower() == raw.lower():
            return s
    return raw[:40]


def fmt_score(score: float | None) -> str:
    """Балл теста для подписей: как хранится, без округления до целого (89.7 -> «89.7», 100.0 -> «100»)."""
    if score is None:
        return "—"
    return f"{score:.1f}".rstrip("0").rstrip(".")
