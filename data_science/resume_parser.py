import io
import re
from pathlib import Path

import fitz
import pytesseract

from PIL import Image

SKILLS = [
    "Python",
    "C#",
    "C++",
    "Java",
    "JavaScript",
    "TypeScript",
    "Go",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "React",
    "Vue",
    "Angular",
    "Django",
    "FastAPI",
    "Flask",
    "Spring",
    "Docker",
    "Kubernetes",
    "Linux",
    "Git",
    "Pandas",
    "NumPy",
    "scikit-learn"
]

STOP_WORDS = {
    "developer", "опыт", "резюме", "backend", "frontend",
    "middle", "senior", "junior", "data", "science",
    "engineer", "cv", "работы", "стаж"
}


def extract_text_from_pdf(
        pdf_path: str,
        use_ocr: bool = True
) -> str:
    pages_text = []

    # Используем контекстный менеджер для надежного закрытия файла
    with fitz.open(pdf_path) as pdf:
        for page in pdf:

            text = page.get_text()

            # Если текстовый PDF – используем
            if text.strip():
                pages_text.append(text)
                continue

            # Если текст отсутствует – OCR
            if use_ocr:
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2)
                )

                image = Image.open(
                    io.BytesIO(pix.tobytes("png"))
                )

                ocr_text = pytesseract.image_to_string(
                    image,
                    lang="rus+eng"
                )

                pages_text.append(ocr_text)

    return "\n".join(pages_text)


def extract_email(text: str) -> str | None:
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return None


def extract_phone(text: str) -> str | None:
    # Исправленный паттерн: разрешает любое количество пробелов, дефисов и скобок между группами цифр
    pattern = (
        r"(?:\+7|8)"
        r"[\s\-()]*"
        r"\d{3}"
        r"[\s\-()]*"
        r"\d{3}"
        r"[\s\-]*"
        r"\d{2}"
        r"[\s\-]*"
        r"\d{2}"
    )

    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return None


def extract_skills(text: str) -> list[str]:
    found_skills = []
    text_lower = text.lower()

    for skill in SKILLS:
        # Используем границы слов (или отсутствие буквенно-цифровых символов) для точного совпадения,
        # чтобы "Java" не находилась внутри "JavaScript" или "Go" внутри "Django".
        escaped_skill = re.escape(skill.lower())
        pattern = r'(?<![\w])' + escaped_skill + r'(?![\w])'

        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return found_skills


def extract_experience(text: str) -> float | None:
    # Привязываем поиск строго к словам "опыт" или "стаж",
    # чтобы не принимать "Возраст 25 лет" за стаж.
    pattern = r"(?:опыт[а]?\s*(?:работы)?|стаж[а]?)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*(?:год|лет|мес)"

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if match:
        return float(
            match.group(1).replace(",", ".")
        )

    # Если стаж не найден, возвращаем None, а не придуманный 0.0
    return None


def extract_name(text: str) -> str | None:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Для MVP используем первую подходящую строку.
    for line in lines[:10]:

        words = line.split()

        if 2 <= len(words) <= 3:

            # Проверяем, что все слова с большой буквы
            if all(word[0].isupper() for word in words if word):

                # Добавлен фильтр стоп-слов, чтобы заголовки типа "Backend Developer" не попали в имя
                if not any(word.lower() in STOP_WORDS for word in words):
                    return line

    return None


def calculate_profile_completeness(profile: dict) -> float:
    fields = [
        profile.get("name"),
        profile.get("email"),
        profile.get("phone"),
        profile.get("skills"),
        profile.get("experience_years"),
    ]

    # None, пустые строки и пустые списки не засчитываются
    filled = sum(
        value not in [None, "", [], 0]
        for value in fields
    )

    return round(
        filled / len(fields),
        2
    )


def parse_resume(pdf_path: str) -> dict:
    text = extract_text_from_pdf(pdf_path)

    profile = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "experience_years": extract_experience(text),
    }

    profile["profile_completeness"] = (
        calculate_profile_completeness(profile)
    )

    profile["raw_text"] = text

    return profile