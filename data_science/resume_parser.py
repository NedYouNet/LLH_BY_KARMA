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


def extract_text_from_pdf(
    pdf_path: str,
    use_ocr: bool = True
) -> str:

    pdf = fitz.open(pdf_path)

    pages_text = []

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

    pdf.close()

    return "\n".join(pages_text)


def extract_email(text: str) -> str | None:

    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return None


def extract_phone(text: str) -> str | None:

    pattern = (
        r"(?:\+7|8)"
        r"[\s\-()]?"
        r"\d{3}"
        r"[\s\-()]?"
        r"\d{3}"
        r"[\s\-]?"
        r"\d{2}"
        r"[\s\-]?"
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

        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


def extract_experience(text: str) -> float:

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*(?:года|лет|год)\s*(?:опыта|стажа)?",
        r"опыт\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*(?:года|лет|год)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return float(
                match.group(1).replace(",", ".")
            )

    return 0.0


def extract_name(text: str) -> str | None:

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Для MVP используем первую подходящую строку.
    # В дальнейшем можно заменить на spaCy NER.
    for line in lines[:10]:

        words = line.split()

        if 2 <= len(words) <= 3:

            if all(
                word[0].isupper()
                for word in words
                if word
            ):
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