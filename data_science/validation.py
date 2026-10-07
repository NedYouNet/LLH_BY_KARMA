import pandas as pd

from data_science.matcher import CandidateMatcher
from data_science.models import Vacancy


def precision_at_k(
    results,
    relevant_ids,
    k=10
):
    top_k = results[:k]

    if not top_k:
        return 0.0

    relevant_count = sum(
        candidate.candidate_id in relevant_ids
        for candidate in top_k
    )

    return relevant_count / len(top_k)


def validate():

    df = pd.read_csv(
        "data_science/data/candidates.csv"
    )

    matcher = CandidateMatcher(df)

    vacancy = Vacancy(
        specialization="Backend",
        grade="Middle",
        required_skills=["C#"]
    )

    results = matcher.rank(
        vacancy,
        limit=10
    )

    # Для синтетического набора
    # эталоном считаем тех,
    # кто действительно соответствует вакансии.
    relevant_ids = set(
        df[
            (df["specialization"] == "Backend")
            &
            (df["grade"] == "Middle")
            &
            (
                df["skills"]
                .str.contains("C#", regex=False)
            )
        ]["id"]
    )

    score = precision_at_k(
        results,
        relevant_ids,
        k=10
    )

    print(
        f"Precision@10: {score:.2%}"
    )


if __name__ == "__main__":
    validate()