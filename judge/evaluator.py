import logging
from pathlib import Path

from app.judge.runner import (
    cleanup_submission_directory,
    prepare_submission_directory,
    run_test_case,
)


logger = logging.getLogger(__name__)

# choose the most serious failure when different tests fail differently
RESULT_PRIORITY = ("SE", "TLE", "RE", "WA")


def choose_overall_result(
    test_results: list[dict],
) -> str:
    """
    choose the final result using the required priority
    """

    if not test_results:
        return "SE"

    if all(
        test_result["result"] == "AC"
        for test_result in test_results
    ):
        return "AC"

    existing_results = {
        test_result["result"]
        for test_result in test_results
    }

    for result in RESULT_PRIORITY:
        if result in existing_results:
            return result

    return "WA"


async def judge_solution(
    submission_id: int,
    source_code: str,
    time_limit: float,
    test_cases: list[dict],
) -> dict:
    """
    execute every testcase and calculate the final score
    """

    submission_directory: Path | None = None
    test_results = []
    total_score = 0
    total_time = 0.0

    try:
        # save the source once and reuse the same file for each testcase
        submission_directory = prepare_submission_directory(
            submission_id,
            source_code,
        )

        for test_case in test_cases:
            execution_result = await run_test_case(
                submission_directory,
                test_case["input_data"],
                test_case["expected_output"],
                time_limit,
            )

            # a testcase awards its full score only when it is accepted
            awarded_score = (
                test_case["score"]
                if execution_result["result"] == "AC"
                else 0
            )
            total_score += awarded_score
            total_time += execution_result["time_used"]

            # preserve all details for role based log views
            test_results.append({
                "case_id": test_case["case_id"],
                "result": execution_result["result"],
                "score": awarded_score,
                "maximum_score": test_case["score"],
                "time_used": execution_result["time_used"],
                "memory_used": execution_result["memory_used"],
                "exit_code": execution_result["exit_code"],
                "input_data": test_case["input_data"],
                "expected_output": test_case[
                    "expected_output"
                ],
                "stdout": execution_result["stdout"],
                "stderr": execution_result["stderr"],
                "message": execution_result["message"],
                "is_hidden": bool(test_case["is_hidden"]),
            })

        return {
            "result": choose_overall_result(test_results),
            "score": total_score,
            "total_time": total_time,
            "cases": test_results,
        }

    except Exception as error:
        logger.exception(
            "evaluator failed for submission %s",
            submission_id,
        )

        return {
            "result": "SE",
            "score": total_score,
            "total_time": total_time,
            "cases": test_results,
            "message": f"{type(error).__name__}: {error}",
        }

    finally:
        # temporary source code must be removed for every result path
        if submission_directory is not None:
            cleanup_submission_directory(
                submission_directory
            )
