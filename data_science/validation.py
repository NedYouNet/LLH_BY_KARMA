import pandas as pd
from data_science.matcher import CandidateMatcher
from data_science.models import Vacancy


def precision_at_k(results, relevant_ids, k=10):
    top_k = results[:k]
    if not top_k:
        return 0.0

    relevant_count = sum(
        candidate.candidate_id in relevant_ids
        for candidate in top_k
    )
    # Делим на длину фактической выдачи, если найдено меньше k кандидатов (как просил ревьюер)
    return relevant_count / len(top_k)


def validate():
    df = pd.read_csv("data_science/data/candidates.csv")
    matcher = CandidateMatcher(df)

    # Тестовые сценарии (разные вакансии)
    test_cases = [
        Vacancy(specialization="backend", grade="middle", required_skills=["C#"]),
        Vacancy(specialization="frontend", grade="senior", required_skills=["React", "TypeScript"]),
        Vacancy(specialization="data_science", grade="junior", required_skills=["Python", "Pandas"]),
        Vacancy(specialization="devops", grade="intern", required_skills=[]),  # Вакансия без навыков
    ]

    print("=== Результаты валидации (Precision@10) ===\n")

    for i, vacancy in enumerate(test_cases, 1):
        results = matcher.rank(vacancy, limit=10)

        # Эталоном считаем тех, кто аппаратно подходит по категории и навыкам
        mask = (df["specialization"] == vacancy.specialization) & (df["grade"] == vacancy.grade)

        # Если есть требования по навыкам, они должны присутствовать
        for skill in vacancy.required_skills:
            mask &= df["skills"].str.contains(skill, regex=False, case=False)

        relevant_ids = set(df[mask]["id"])

        score = precision_at_k(results, relevant_ids, k=10)

        print(f"Кейс {i}: {vacancy.specialization.capitalize()} {vacancy.grade.capitalize()}")
        print(f"Требуемые навыки: {', '.join(vacancy.required_skills) if vacancy.required_skills else 'Нет'}")
        print(f"Найдено в топе: {len(results)}")
        print(f"Precision@10: {score:.2%}\n")


if __name__ == "__main__":
    validate()