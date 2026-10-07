import random
import pandas as pd

from faker import Faker


fake = Faker("ru_RU")


SPECIALIZATIONS = {
    "Backend": [
        "Python",
        "C#",
        "Java",
        "Go",
        "C++"
    ],
    "Frontend": [
        "JavaScript",
        "TypeScript",
        "React",
        "Vue",
        "Angular"
    ],
    "Data Science": [
        "Python",
        "SQL",
        "Pandas",
        "NumPy",
        "scikit-learn"
    ],
    "DevOps": [
        "Docker",
        "Kubernetes",
        "Linux",
        "GitLab CI",
        "Terraform"
    ]
}


GRADES = [
    "Junior",
    "Middle",
    "Senior"
]


def generate_candidate(candidate_id: int, has_fsp: bool) -> dict:
    # Выбираем специализацию
    specialization = random.choice(
        list(SPECIALIZATIONS.keys())
    )

    # Получаем навыки этой специализации
    specialization_skills = SPECIALIZATIONS[specialization]

    # Случайное количество навыков
    skills_count = random.randint(
        2,
        len(specialization_skills)
    )

    # Выбираем навыки
    skills = random.sample(
        specialization_skills,
        skills_count
    )

    # Выбираем грейд
    grade = random.choice(GRADES)

    # Опыт зависит от грейда
    if grade == "Junior":
        experience = round(
            random.uniform(0.5, 2.0),
            1
        )

    elif grade == "Middle":
        experience = round(
            random.uniform(2.0, 5.0),
            1
        )

    else:
        experience = round(
            random.uniform(5.0, 12.0),
            1
        )

    # FSP
    if has_fsp:
        fsp_id = f"FSP-{candidate_id:05d}"
        fsp_achievements = random.randint(1, 5)
    else:
        fsp_id = None
        fsp_achievements = 0

    # Полнота профиля
    profile_fields = [
        True,  # name
        True,  # email
        True,  # phone
        True,  # specialization
        True,  # grade
        len(skills) > 0,
        experience > 0,
        has_fsp
    ]

    profile_completeness = (
        sum(profile_fields) / len(profile_fields)
    )

    # Результат теста
    if grade == "Junior":
        test_result = random.uniform(50, 75)

    elif grade == "Middle":
        test_result = random.uniform(70, 90)

    else:
        test_result = random.uniform(85, 100)

    return {
        "id": candidate_id,

        "name": fake.name(),

        "email": fake.email(),

        "phone": fake.phone_number(),

        "specialization": specialization,

        "grade": grade,

        "skills": ", ".join(skills),

        "experience_years": experience,

        "test_result": round(
            test_result,
            2
        ),

        "fsp_id": fsp_id,

        "fsp_achievements": fsp_achievements,

        "profile_completeness": round(
            profile_completeness,
            2
        )
    }


def generate_dataset(
    count: int = 500,
    output_path: str = "data_science/data/candidates.csv"
) -> pd.DataFrame:

    if count < 2:
        raise ValueError(
            "Количество кандидатов должно быть >= 2"
        )

    candidates = []

    # Примерно половина кандидатов имеет FSP ID
    fsp_count = count // 2

    for candidate_id in range(1, count + 1):

        has_fsp = candidate_id <= fsp_count

        candidate = generate_candidate(
            candidate_id,
            has_fsp
        )

        candidates.append(candidate)

    # Создаём DataFrame
    df = pd.DataFrame(candidates)

    # Сохраняем CSV
    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    return df


if __name__ == "__main__":

    df = generate_dataset()

    print(
        "Создано кандидатов:",
        len(df)
    )

    print(
        "С FSP ID:",
        df["fsp_id"].notna().sum()
    )

    print(
        "Без FSP ID:",
        df["fsp_id"].isna().sum()
    )

    print()

    print(df.head())