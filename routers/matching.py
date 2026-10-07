from fastapi import APIRouter
from data_science.matcher import CandidateMatcher
from data_science.models import Vacancy
import pandas as pd

router = APIRouter(prefix="/api/matching", tags=["Matching"])

candidates_df = pd.read_csv("data_science/data/candidates.csv")
matcher = CandidateMatcher(candidates_df)

@router.post("/")
def matching(vacancy: Vacancy):
    candidates = matcher.rank(vacancy=vacancy, limit=20)
    return {
        "count": len(candidates),
        "candidates": [candidate.model_dump() for candidate in candidates]
    }