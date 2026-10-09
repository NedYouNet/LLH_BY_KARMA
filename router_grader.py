from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from invariants import TASK_INVARIANTS
from autograder import analyze_complexity, run_code_in_sandbox, calculate_candidate_score

router = APIRouter()


class SubmissionRequest(BaseModel):
    task_id: str
    candidate_code: str
    candidate_cv_grade: str = "Junior"  # Грейд, который мы ранее достали парсером


class GraderResponse(BaseModel):
    tests_passed: int
    total_tests: int
    ast_complexity: str
    final_score: float
    details: list


@router.post("/api/grader/submit", response_model=GraderResponse)
def submit_solution(submission: SubmissionRequest):
    invariant = TASK_INVARIANTS.get(submission.task_id)
    if not invariant:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    hidden_tests = invariant.get("hidden_tests", [])
    if not hidden_tests:
        raise HTTPException(status_code=500, detail="Для данной задачи нет автотестов")

    # 1. Статический анализ AST
    complexity = analyze_complexity(submission.candidate_code)

    # 2. Запуск в песочнице
    tests_passed = 0
    details = []

    for idx, test in enumerate(hidden_tests):
        # Превращаем входные кортежи/списки в строки для передачи через stdin
        test_input_str = "\n".join(map(str, test["input"])) if isinstance(test["input"], (list, tuple)) else str(
            test["input"])
        expected_out_str = str(test["expected"])

        result = run_code_in_sandbox(submission.candidate_code, test_input_str, expected_out_str)

        if result["success"]:
            tests_passed += 1

        details.append({
            "test_number": idx + 1,
            "success": result["success"],
            "error": result["error"]
        })

    # 3. Умный скоринг
    final_score = calculate_candidate_score(
        tests_passed=tests_passed,
        total_tests=len(hidden_tests),
        complexity=complexity,
        cv_grade=submission.candidate_cv_grade
    )

    return GraderResponse(
        tests_passed=tests_passed,
        total_tests=len(hidden_tests),
        ast_complexity=complexity,
        final_score=final_score,
        details=details
    )