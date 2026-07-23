import logging
from pathlib import Path

from app.judge.runner import (
    cleanup_submission_directory,
    prepare_submission_directory,
    run_test_case,
)


logger = logging.getLogger(__name__)


RESULT_PRIORITY = (
    "SE",
    "TLE",
    "RE",
    "WA",
)


def choose_overall_result(
    test_results: list[dict],
) -> str:
    """
    choose the final submission result
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


def _create_test_log(
    test_case: dict,
    execution_result: dict,
    awarded_score: int,
) -> dict:
    """
    combine testcase data and execution data
    """

    return {
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
        "is_hidden": bool(
            test_case["is_hidden"]
        ),
    }


async def judge_solution(
    submission_id: int,
    source_code: str,
    time_limit: float,
    test_cases: list[dict],
) -> dict:
    """
    execute every testcase with its own full time limit
    """

    submission_directory: Path | None = None
    test_results: list[dict] = []
    total_score = 0
    total_time = 0.0

    try:
        submission_directory = (
            prepare_submission_directory(
                submission_id,
                source_code,
            )
        )

        for test_case in test_cases:
            # pass the complete time limit to every testcase
            execution_result = await run_test_case(
                submission_directory,
                test_case["input_data"],
                test_case["expected_output"],
                time_limit,
            )

            # total time is only a submission statistic
            total_time += execution_result[
                "time_used"
            ]

            awarded_score = (
                test_case["score"]
                if execution_result["result"] == "AC"
                else 0
            )

            total_score += awarded_score

            test_results.append(
                _create_test_log(
                    test_case,
                    execution_result,
                    awarded_score,
                )
            )

        return {
            "result": choose_overall_result(
                test_results
            ),
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
            "message": (
                f"{type(error).__name__}: {error}"
            ),
        }

    finally:
        if submission_directory is not None:
            cleanup_submission_directory(
                submission_directory
            )
