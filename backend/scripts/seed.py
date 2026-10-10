"""
Наполнение базы демо-данными: 200 кандидатов (50 с достижениями ФСП), 6 компаний, 20 вакансий,
приглашения, отклики и короткие задания. Платформа на демо выглядит «живой».

Запуск (из папки backend):
    python -m scripts.seed            # добавить данные
    python -m scripts.seed --reset    # очистить все таблицы и залить заново

Демо-аккаунты (пароль у всех: demo12345):
    candidate@demo.ru   — кандидат, прошёл тест, есть ФСП, есть входящее приглашение
    newbie@demo.ru      — кандидат «с нуля»: только зарегистрирован (для показа онбординга)
    employer@demo.ru    — работодатель «ООО Цифровые Решения» с вакансиями
"""
import argparse
import random
import re
from datetime import timedelta

from faker import Faker
from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine, utcnow
from app.core.security import hash_password
from app.models import (
    Application, CandidateProfile, EmployerProfile, GradeHistory, Invitation, ShortTask, ShortTaskSubmission, User,
    Vacancy,
)
from app.reference import GRADE_CODES, SKILLS, SOFT_SKILLS, TEAM_ROLES
from app.services.fsp_service import MockFspRegistry, compute_fsp_score

fake = Faker("ru_RU")
rng = random.Random(2026)
Faker.seed(2026)
PASSWORD = "demo12345"
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", "Нижний Новгород", "Томск", "Самара"]
SPEC_WEIGHTS = {"backend": 0.35, "frontend": 0.25, "data_science": 0.15, "qa": 0.13, "devops": 0.12}
GRADE_WEIGHTS = [0.12, 0.38, 0.33, 0.17]
EXP_BY_GRADE = {"intern": (0, 0.5), "junior": (0.5, 2), "middle": (2, 4.5), "senior": (4.5, 10)}

COMPANIES = [
    ("ООО Цифровые Решения", "fintech", "Платёжная инфраструктура для банков и маркетплейсов", "7701234567"),
    ("АО ТехноСфера", "telecom", "Цифровые сервисы для операторов связи", "7809876543"),
    ("ООО ГеймЛаб", "gamedev", "Мобильные игры с аудиторией 5 млн игроков", None),
    ("ООО ЭдТех Про", "edtech", "Платформа онлайн-обучения программированию", "1655012345"),
    ("ООО МедИнфо", "medtech", "Медицинские информационные системы", None),
    ("АО ПромАналитика", "industry", "Предиктивная аналитика для заводов", "6658123456"),
]

VACANCIES = [
    ("backend", "middle", "Python-разработчик в платёжную команду",
     "Разрабатываем API платежей на FastAPI, PostgreSQL и Kafka. Высокая нагрузка, микросервисы, идемпотентность.",
     ["Python", "FastAPI", "PostgreSQL", "Kafka", "Docker"], (220000, 300000)),
    ("backend", "junior", "Junior Python-разработчик", "Внутренние сервисы на Django, REST API, SQL-запросы, код-ревью с ментором.",
     ["Python", "Django", "PostgreSQL", "Git"], (100000, 150000)),
    ("backend", "senior", "Senior Go-разработчик", "Проектирование высоконагруженных сервисов, gRPC, Kubernetes, менторство.",
     ["Go", "gRPC", "PostgreSQL", "Kubernetes", "Kafka"], (350000, 450000)),
    ("backend", "middle", "Java-разработчик (Spring)", "Сервисы биллинга на Spring Boot, RabbitMQ, Oracle/PostgreSQL.",
     ["Java", "Spring", "PostgreSQL", "RabbitMQ"], (230000, 290000)),
    ("backend", "intern", "Стажёр-бэкендер", "Стажировка: Python, SQL, первые задачи в продакшене под присмотром наставника.",
     ["Python", "SQL", "Git"], (50000, 70000)),
    ("frontend", "middle", "React-разработчик", "Личный кабинет клиента на React + TypeScript, дизайн-система, тесты Jest.",
     ["React", "TypeScript", "Redux", "Jest"], (200000, 260000)),
    ("frontend", "junior", "Junior Vue-разработчик", "Админ-панели на Vue 3, TailwindCSS, интеграция с REST API.",
     ["Vue", "JavaScript", "TailwindCSS", "REST"], (90000, 140000)),
    ("frontend", "senior", "Senior Frontend / Next.js", "SSR-витрина, производительность, архитектура фронтенда.",
     ["Next.js", "React", "TypeScript", "Webpack"], (320000, 400000)),
    ("data_science", "middle", "Data Scientist (рекомендации)", "Рекомендательные модели, CatBoost, A/B-тесты, pandas, SQL.",
     ["Python", "pandas", "CatBoost", "SQL", "Statistics"], (230000, 300000)),
    ("data_science", "junior", "Junior ML-инженер (NLP)", "Классификация обращений, трансформеры, разметка данных.",
     ["Python", "PyTorch", "NLP", "pandas"], (120000, 170000)),
    ("data_science", "senior", "Lead CV-инженер", "Компьютерное зрение для контроля качества на производстве.",
     ["Python", "PyTorch", "Computer Vision", "Spark"], (380000, 480000)),
    ("qa", "junior", "QA-инженер (ручное + API)", "Тестирование API в Postman, тест-дизайн, баг-репорты.",
     ["Postman", "REST", "SQL", "Test design"], (80000, 120000)),
    ("qa", "middle", "QA Automation (Python)", "Автотесты на pytest + Playwright, CI, Allure-отчёты.",
     ["Python", "pytest", "Playwright", "Allure", "CI/CD"], (180000, 240000)),
    ("qa", "senior", "Lead QA", "Стратегия тестирования, нагрузочное тестирование JMeter, команда из 5 QA.",
     ["JMeter", "Test design", "CI/CD", "Python"], (280000, 340000)),
    ("devops", "middle", "DevOps-инженер", "Kubernetes, Terraform, GitLab CI, мониторинг Prometheus/Grafana.",
     ["Kubernetes", "Terraform", "GitLab CI", "Prometheus"], (230000, 300000)),
    ("devops", "junior", "Junior DevOps", "Docker, Linux, CI/CD пайплайны, поддержка стендов.",
     ["Docker", "Linux", "CI/CD", "Bash"], (100000, 150000)),
    ("devops", "senior", "SRE", "SLO, инцидент-менеджмент, отказоустойчивость, Yandex Cloud.",
     ["Kubernetes", "Prometheus", "Go", "Yandex Cloud"], (350000, 450000)),
    ("backend", "middle", "Node.js-разработчик", "BFF на Node.js, GraphQL, Redis.",
     ["Node.js", "GraphQL", "Redis", "Docker"], (200000, 260000)),
    ("frontend", "middle", "Angular-разработчик", "Корпоративный портал на Angular, RxJS.",
     ["Angular", "TypeScript", "REST"], (190000, 250000)),
    ("data_science", "middle", "Аналитик-разработчик данных", "Airflow-пайплайны, Spark, витрины данных.",
     ["Airflow", "Spark", "SQL", "Python"], (210000, 270000)),
]

SHORT_TASKS = [
    ("backend", "Как бы вы спроектировали rate limiter на 100 rps на пользователя?", "approach"),
    ("backend", "Найдите N+1 в коде ORM-запроса и предложите исправление", "solution"),
    ("frontend", "Как ускорить первую отрисовку страницы каталога?", "approach"),
    ("data_science", "Как бы вы оценили качество рекомендаций без онлайн-теста?", "approach"),
    ("qa", "Составьте чек-лист проверки формы регистрации", "solution"),
    ("devops", "Как организовать zero-downtime деплой для монолита?", "approach"),
]


# Современные имена (Faker выдаёт и старинные — «Фёкла», «Антип», — что на демо выглядит странно)
MALE_NAMES = ["Александр", "Алексей", "Андрей", "Артём", "Владимир", "Георгий", "Даниил", "Денис", "Дмитрий",
              "Егор", "Иван", "Игорь", "Илья", "Кирилл", "Максим", "Марк", "Матвей", "Михаил", "Никита", "Николай",
              "Олег", "Павел", "Роман", "Сергей", "Степан", "Тимофей", "Фёдор", "Ярослав"]
FEMALE_NAMES = ["Алина", "Алиса", "Анастасия", "Анна", "Арина", "Валерия", "Варвара", "Вероника", "Виктория",
                "Дарья", "Диана", "Екатерина", "Елизавета", "Ксения", "Мария", "Милана", "Наталья", "Ольга",
                "Полина", "Софья", "Татьяна", "Ульяна", "Юлия", "Яна"]

# Осмысленные тексты для демо (Faker на русском даёт бессвязный набор слов — для показа не годится)
SPEC_RU = {"backend": "Бэкенд", "frontend": "Фронтенд", "data_science": "Data Science", "qa": "Тестирование",
           "devops": "DevOps"}
GRADE_RU = {"intern": "стажёр", "junior": "Junior", "middle": "Middle", "senior": "Senior"}

ABOUT_INTRO = {
    "backend": ["Бэкенд-разработчик, пишу API и сервисы для веба.",
                "Разрабатываю серверную часть: API, базы данных, интеграции.",
                "Люблю проектировать надёжные сервисы и чистые API."],
    "frontend": ["Фронтенд-разработчик, делаю удобные интерфейсы.",
                 "Верстаю и программирую интерфейсы веб-приложений.",
                 "Делаю быстрые и аккуратные интерфейсы, внимательно отношусь к деталям."],
    "data_science": ["Занимаюсь анализом данных и машинным обучением.",
                     "Строю модели и довожу их до продакшена.",
                     "Работаю с данными: от SQL-выгрузок до обучения моделей."],
    "qa": ["QA-инженер, отвечаю за качество релизов.",
           "Тестирую веб-приложения и API, пишу автотесты.",
           "Ищу баги до пользователей: тест-дизайн, API, автоматизация."],
    "devops": ["DevOps-инженер, автоматизирую сборку и доставку.",
               "Настраиваю инфраструктуру, CI/CD и мониторинг.",
               "Слежу, чтобы сервисы работали стабильно и выкатывались без простоя."],
}
ABOUT_EXP = {
    "intern": ["Учусь в вузе, сделал(а) несколько учебных и командных проектов.",
               "Участвовал(а) в хакатонах, ищу первую стажировку."],
    "junior": ["Есть опыт коммерческой разработки в небольшой команде.",
               "Работал(а) над внутренними сервисами под руководством ментора."],
    "middle": ["Самостоятельно веду задачи от постановки до релиза, участвую в код-ревью.",
               "Несколько лет в продуктовой команде, отвечал(а) за отдельный модуль."],
    "senior": ["Проектирую архитектуру, менторю младших коллег, отвечаю за технические решения.",
               "Руководил(а) технической частью проектов, выстраивал(а) процессы в команде."],
}
ABOUT_GOAL = ["Хочу расти в продуктовой компании.", "Интересны задачи с высокой нагрузкой.",
              "Ищу команду с сильной инженерной культурой.", "Готов(а) к удалённой работе и командировкам.",
              "Интересуют финтех и образовательные проекты."]

INVITE_TEMPLATES = [
    "{name}, добрый день! Нам подходит ваш профиль: {category}, опыт с {skills}. "
    "Приглашаем на интервью на позицию «{title}».",
    "Здравствуйте, {name}! Ищем человека в команду на позицию «{title}». "
    "Ваш опыт с {skills} пригодится в нашей команде. Будем рады пообщаться.",
    "{name}, привет! Увидели ваш профиль в категории {category} и хотим познакомиться. "
    "Расскажем о задачах и команде на коротком созвоне.",
]
COVER_TEMPLATES = [
    "Здравствуйте! Меня заинтересовала вакансия «{title}». Работал(а) с {skills}, готов(а) пройти интервью.",
    "Добрый день! Мой опыт и стек ({skills}) подходят под требования вакансии «{title}». Буду рад(а) обсудить.",
    "Откликаюсь на вакансию «{title}». Есть опыт с {skills}, могу выйти в течение двух недель.",
]
SHORT_ANSWER = {
    "approach": "Подход по шагам: уточнить требования и ограничения, выбрать решение, оценить риски "
                "и договориться, как проверить результат.",
    "solution": "Решение с пояснениями к каждому шагу; отдельно перечислены учтённые крайние случаи.",
}


MALE: dict[int, bool] = {}  # id кандидата -> пол, чтобы тексты были в правильном роде


def gender(text_: str, male: bool) -> str:
    """«Работал(а)» -> «Работал» / «Работала»."""
    return re.sub(r"\(а\)", "" if male else "а", text_)


def first_name(c: CandidateProfile) -> str:
    return (c.full_name or "").split(" ")[0] or "Здравствуйте"


def category_ru(c: CandidateProfile) -> str:
    spec, grade = c.effective_specialization, c.effective_grade
    return f"«{SPEC_RU.get(spec, spec)} · {GRADE_RU.get(grade, grade)}»"


def reset(db) -> None:
    tables = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if engine.dialect.name == "postgresql":
        db.execute(text("TRUNCATE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"))
    else:
        for t in tables:
            db.execute(text(f"DELETE FROM {t}"))
    db.commit()


def make_user(db, email: str, role: str, pw_hash: str) -> User:
    u = User(email=email, password_hash=pw_hash, role=role, is_email_verified=True)
    db.add(u)
    db.flush()
    return u


def make_candidate(db, pw_hash: str, idx: int, with_fsp: bool, email: str | None = None,
                   spec: str | None = None, grade: str | None = None, full_name: str | None = None,
                   verified: bool = True) -> CandidateProfile:
    """verified=False — анкета заполнена, но тест ещё не пройден: виден работодателям с пометкой «не подтверждён»."""
    spec = spec or rng.choices(list(SPEC_WEIGHTS), weights=list(SPEC_WEIGHTS.values()))[0]
    grade = grade or rng.choices(GRADE_CODES, weights=GRADE_WEIGHTS)[0]
    male = rng.random() < 0.6
    name = full_name or (f"{rng.choice(MALE_NAMES)} {fake.last_name_male()}" if male
                         else f"{rng.choice(FEMALE_NAMES)} {fake.last_name_female()}")
    user = make_user(db, email or f"cand{idx}@demo.ru", "candidate", pw_hash)
    lo, hi = EXP_BY_GRADE[grade]
    skills = rng.sample(SKILLS[spec], k=rng.randint(4, 8))
    score = round(min(100, max(70, rng.gauss(83, 8))), 1)
    now = utcnow()
    assigned = now - timedelta(days=rng.randint(5, 200))
    c = CandidateProfile(
        user_id=user.id, full_name=name, phone=fake.phone_number(), telegram="@" + fake.user_name(),
        contact_email=user.email, city=rng.choice(CITIES), skills=skills,
        soft_skills=rng.sample(SOFT_SKILLS, 3), team_roles=rng.sample(TEAM_ROLES[:3], 1),
        experience_years=round(rng.uniform(lo, hi), 1), work_format=rng.choice(["office", "remote", "hybrid"]),
        desired_salary_from=rng.choice([None, 90000, 150000, 220000, 300000]),
        about=gender(f"{rng.choice(ABOUT_INTRO[spec])} {rng.choice(ABOUT_EXP[grade])} "
                     f"Основной стек: {', '.join(skills[:4])}. {rng.choice(ABOUT_GOAL)}", male),
        industry=rng.choice(["fintech", "ecommerce", "edtech", "telecom", "other"]),
        survey={"specialization": spec, "declared_grade": grade, "skills": skills, "submitted_at": assigned.isoformat()},
        declared_grade=grade, declared_specialization=spec,
        specialization=spec if verified else None, grade=grade if verified else None,
        test_score=score if verified else None,
        skill_scores={s: round(rng.uniform(0.5, 1.0), 2) for s in skills[:3]} if verified else {},
        grade_assigned_at=assigned if verified else None, grade_changed_at=assigned if verified else None,
        consent_processing=True, consent_publication=rng.random() > 0.03, consent_at=assigned,
        last_activity_at=now - timedelta(days=rng.choice([1, 3, 7, 15, 30, 60, 120])),
    )
    if with_fsp:
        fsp_id = str(rng.randint(10000, 99999)) + str(rng.randint(1, 9))  # не оканчивается на 0 -> есть соревнования
        data = MockFspRegistry().get_participant(fsp_id)
        c.fsp_id, c.fsp_achievements, c.fsp_rank = fsp_id, data["achievements"], data["sport_rank"]
        c.fsp_score, c.fsp_synced_at = compute_fsp_score(data["achievements"]), now
    db.add(c)
    db.flush()
    MALE[c.id] = male
    if verified:
        db.add(GradeHistory(candidate_id=c.id, specialization=spec, old_grade=None, new_grade=grade,
                            reason=f"Тест {score:.0f}/100", changed_at=assigned))
    return c


def main(do_reset: bool) -> None:
    db = SessionLocal()
    if do_reset:
        reset(db)
    if db.query(User).filter(User.email == "employer@demo.ru").first():
        print("Демо-данные уже есть. Запустите с --reset, чтобы пересоздать.")
        return
    pw = hash_password(PASSWORD)  # один хеш на всех демо-пользователей — сид работает быстро

    employers = []
    for i, (name, industry, descr, inn) in enumerate(COMPANIES):
        u = make_user(db, "employer@demo.ru" if i == 0 else f"hr{i}@demo.ru", "employer", pw)
        e = EmployerProfile(user_id=u.id, company_name=name, industry=industry, description=descr, inn=inn,
                            city=rng.choice(CITIES[:3]), website=f"https://example-{i}.ru", contact_name=f"{rng.choice(FEMALE_NAMES)} {fake.last_name_female()}",
                            contact_email=u.email, contact_telegram="@hr_" + fake.user_name(),
                            trust_level="inn_provided" if inn else "unverified")
        db.add(e)
        db.flush()
        employers.append(e)

    vacancies = []
    for i, (spec, grade, title, descr, skills, (sf, st)) in enumerate(VACANCIES):
        v = Vacancy(employer_id=employers[i % len(employers)].id, title=title, description=descr, specialization=spec,
                    grade=grade, skills=skills, salary_from=sf, salary_to=st,
                    work_format=rng.choice(["remote", "hybrid", "office"]), city=rng.choice(CITIES[:3]))
        db.add(v)
        vacancies.append(v)
    db.flush()

    candidates = [make_candidate(db, pw, 0, True, email="candidate@demo.ru", spec="backend", grade="middle",
                                 full_name="Алексей Смирнов")]
    demo = candidates[0]
    demo.skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Kafka", "Алгоритмы"]
    demo.about = ("Бэкенд-разработчик, 3 года пишу высоконагруженные API на Python и FastAPI. "
                  "Проектировал платёжный шлюз на PostgreSQL и Kafka, настраивал CI/CD и Docker. "
                  "Призёр соревнований ФСП по продуктовому программированию.")
    demo.experience_years, demo.city, demo.test_score, demo.work_format = 3.2, "Москва", 88.0, "remote"
    demo.phone, demo.telegram = "+79991234567", "@alexey_dev"
    fsp = MockFspRegistry().get_participant("100098")  # сильный профиль ФСП для демонстрации
    demo.fsp_id, demo.fsp_achievements, demo.fsp_score = "100098", fsp["achievements"], compute_fsp_score(fsp["achievements"])
    demo.fsp_rank = fsp["sport_rank"]
    demo.last_activity_at = utcnow() - timedelta(days=1)
    for i in range(1, 200):
        # последние 25 — заполнили анкету, но тест ещё не прошли: видны с пометкой «грейд не подтверждён»
        candidates.append(make_candidate(db, pw, i, with_fsp=i < 50, verified=i < 175))

    newbie = make_user(db, "newbie@demo.ru", "candidate", pw)
    db.add(CandidateProfile(user_id=newbie.id, full_name="Мария Новикова", contact_email=newbie.email))

    # Приглашения: демо-кандидату + случайные, со всеми статусами
    statuses = ["sent", "viewed", "accepted", "declined"]
    demo_v = vacancies[0]
    db.add(Invitation(employer_id=demo_v.employer_id, candidate_id=candidates[0].id, vacancy_id=demo_v.id,
                      position_title=demo_v.title, message="Алексей, видели ваш результат теста и призовые места ФСП. "
                      "Хотим пригласить на интервью в платёжную команду.", salary_from=240000, salary_to=300000,
                      contact_method="Telegram @hr_digital", status="sent", match_score=86.5,
                      match_reasons=[{"type": "test", "label": "Бэкенд · Middle: тест 88/100", "positive": True}]))
    emp_by_id = {e.id: e for e in employers}
    for c in rng.sample(candidates[1:], 25):
        # приглашение — на настоящую вакансию той же специализации, с её названием и вилкой
        same = [v for v in vacancies if v.specialization == c.effective_specialization] or vacancies
        v = rng.choice(same)
        e = emp_by_id[v.employer_id]
        st = rng.choice(statuses)
        msg = rng.choice(INVITE_TEMPLATES).format(name=first_name(c), title=v.title, category=category_ru(c),
                                                  skills=", ".join(c.skills[:3]))
        db.add(Invitation(employer_id=e.id, candidate_id=c.id, vacancy_id=v.id, position_title=v.title, message=msg,
                          salary_from=v.salary_from, salary_to=v.salary_to, contact_method=e.contact_email, status=st,
                          viewed_at=utcnow() if st != "sent" else None,
                          responded_at=utcnow() if st in ("accepted", "declined") else None))

    for c in rng.sample(candidates[1:], 30):  # отклики
        same = [v for v in vacancies if v.specialization == c.specialization]
        if same:
            v = rng.choice(same)
            letter = gender(rng.choice(COVER_TEMPLATES).format(title=v.title, skills=", ".join(c.skills[:3])),
                            MALE.get(c.id, True))
            db.add(Application(candidate_id=c.id, vacancy_id=v.id, cover_letter=letter,
                               status=rng.choice(["sent", "viewed", "accepted", "rejected"])))

    for spec, title, kind in SHORT_TASKS:  # короткие задания
        t = ShortTask(employer_id=rng.choice(employers).id, title=title, description=title + ". Опишите кратко.",
                      kind=kind, specialization=spec)
        db.add(t)
        db.flush()
        for c in [c for c in candidates if c.specialization == spec][:6]:
            score = rng.choice([6, 7, 8, 9, 10])
            db.add(ShortTaskSubmission(task_id=t.id, candidate_id=c.id, answer=SHORT_ANSWER[kind], status="reviewed",
                                       employer_score=score, reviewed_at=utcnow()))
            c.short_tasks_done += 1
            c.short_tasks_avg = score if c.short_tasks_avg is None else (c.short_tasks_avg + score) / 2
    db.commit()
    print(f"Готово: {len(candidates)} кандидатов ({sum(1 for c in candidates if c.fsp_id)} с ФСП, "
          f"{sum(1 for c in candidates if not c.grade)} без пройденного теста), "
          f"{len(employers)} компаний, {len(vacancies)} вакансий. Пароль демо-аккаунтов: {PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Очистить таблицы перед заливкой")
    main(parser.parse_args().reset)
