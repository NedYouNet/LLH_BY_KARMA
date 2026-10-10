import pandas as pd
from data_science.models import Vacancy, RankedCandidate

# Обновляем веса, выделяя долю для совпадения навыков
TEST_WEIGHT = 0.40
FSP_WEIGHT = 0.25
SKILLS_WEIGHT = 0.25
PROFILE_WEIGHT = 0.10


class CandidateMatcher:

    def __init__(self, candidates: pd.DataFrame):
        self.candidates = candidates.copy()
        # Предварительно обрабатываем скиллы для быстрого поиска (превращаем строки в множества)
        self.candidates['skills_set'] = self.candidates['skills'].apply(
            lambda x: set([s.strip().lower() for s in str(x).split(',')]) if pd.notna(x) else set()
        )

    def hard_filter(self, vacancy: Vacancy) -> pd.DataFrame:
        df = self.candidates.copy()

        # 1. Фильтрация по специализации (Оставляем)
        df = df[df["specialization"].str.lower() == vacancy.specialization.lower()]

        # 2. Фильтрация по грейду (Оставляем)
        df = df[df["grade"].str.lower() == vacancy.grade.lower()]

        # 3. Фильтрацию по скиллам УБРАЛИ. Теперь они влияют на ранжирование, а не отсекают кандидата.
        return df

    @staticmethod
    def calculate_fsp_score(row) -> float:
        if pd.isna(row["fsp_id"]):
            return 0.0
        achievements = min(int(row["fsp_achievements"]), 5)
        return achievements / 5

    @staticmethod
    def calculate_skills_score(candidate_skills: set, required_skills: list) -> float:
        if not required_skills:
            return 1.0  # Если работодатель не указал навыки, совпадение 100%

        req_set = set([s.lower() for s in required_skills])
        intersection = candidate_skills.intersection(req_set)

        # Возвращаем процент совпадения (от 0.0 до 1.0)
        return len(intersection) / len(req_set)

    # Исправлена аннотация (теперь 5 элементов) и приведение всех баллов к шкале 0-100
    def calculate_score(self, row, vacancy: Vacancy) -> tuple[float, float, float, float, float]:
        test_score = row["test_result"] / 100
        fsp_score = self.calculate_fsp_score(row)
        profile_score = float(row["profile_completeness"])

        skills_score = self.calculate_skills_score(
            row["skills_set"],
            vacancy.required_skills
        )

        score = (
                TEST_WEIGHT * test_score
                + FSP_WEIGHT * fsp_score
                + SKILLS_WEIGHT * skills_score
                + PROFILE_WEIGHT * profile_score
        )

        if not row.get("is_grade_confirmed", False):
            score = score * 0.5

        return (
            round(score * 100, 2),
            round(test_score * 100, 2),
            round(fsp_score * 100, 2),
            round(profile_score * 100, 2),
            round(skills_score * 100, 2)
        )

    @staticmethod
    def build_explanation(row, fsp_score: float, skills_score: float) -> list[str]:
        explanation = []

        # Честно пишем работодателю про грейд в самом начале объяснения
        if row.get("is_grade_confirmed", False):
            explanation.append("Заявленный грейд подтвержден тестом")
        else:
            explanation.append("Тест на заявленный грейд не пройден")

        # Значение skills_score теперь передается уже в шкале 0-100, поэтому умножать на 100 не нужно
        explanation.append(f"Совпадение по стеку: {skills_score:.0f}%")
        explanation.append(f"Результат теста: {row['test_result']:.1f}%")

        if pd.notna(row["fsp_id"]):
            explanation.append(f"Подтверждённые достижения ФСП: {int(row['fsp_achievements'])}")
        else:
            explanation.append("Подтверждённые достижения ФСП отсутствуют")

        explanation.append(f"Заполненность профиля: {row['profile_completeness'] * 100:.0f}%")
        return explanation

    def rank(self, vacancy: Vacancy, limit: int = 20) -> list[RankedCandidate]:
        filtered = self.hard_filter(vacancy)

        if filtered.empty:
            return []

        filtered = filtered.copy()

        # Применяем новую функцию вычисления скора
        scores_data = filtered.apply(lambda row: self.calculate_score(row, vacancy), axis=1)

        # Распаковываем результаты вычислений обратно в DataFrame
        filtered[["score", "test_score", "fsp_score", "profile_score", "skills_score"]] = pd.DataFrame(
            scores_data.tolist(), index=filtered.index)

        # Жесткая сортировка: неподтвержденные грейды гарантированно отправляются в самый низ списка
        filtered = filtered.sort_values(
            by=["is_grade_confirmed", "score"],
            ascending=[False, False]
        ).head(limit)

        result = []
        for _, row in filtered.iterrows():
            result.append(
                RankedCandidate(
                    candidate_id=int(row["id"]),
                    score=float(row["score"]),
                    test_score=float(row["test_score"]),
                    fsp_score=float(row["fsp_score"]),
                    profile_score=float(row["profile_score"]),
                    skills_score=float(row["skills_score"]),
                    is_grade_confirmed=bool(row.get("is_grade_confirmed", False)),
                    explanation=self.build_explanation(row, row["fsp_score"], row["skills_score"])
                )
            )

        return result