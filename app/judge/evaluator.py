import logging
from pathlib import Path

from app.judge.runner import (
    cleanup_submission_directory,
    prepare_submission_directory,
    run_test_case,
)


logger = logging.getLogger(__name__)

# choose the most serious failure among all completed tests
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


def _create_test_log(
    test_case: dict,
    execution_result: dict,
    awarded_score: int,
) -> dict:
    """
    combine testcase data with its execution result
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


def _total_time_limit_result() -> dict:
    """
    create a tle result when no total time remains
    """

    return {
        "result": "TLE",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "time_used": 0.0,
        "memory_used": None,
        "message": "total time limit exceeded",
    }


async def judge_solution(
    submission_id: int,
    source_code: str,
    time_limit: float,
    test_cases: list[dict],
) -> dict:
    """
    execute tests within one shared submission time limit
    """

    submission_directory: Path | None = None
    test_results: list[dict] = []
    total_score = 0
    total_time = 0.0

    try:
        # save the submitted source code only once
        submission_directory = (
            prepare_submission_directory(
                submission_id,
                source_code,
            )
        )

        for test_case in test_cases:
            # calculate how much time remains for the whole submission
            remaining_time = (
                time_limit - total_time
            )

            if remaining_time <= 0:
                execution_result = (
                    _total_time_limit_result()
                )
            else:
                # each next test receives only the remaining total time
                execution_result = await run_test_case(
                    submission_directory,
                    test_case["input_data"],
                    test_case["expected_output"],
                    remaining_time,
                )

            # add the actual time used by this testcase
            total_time += execution_result[
                "time_used"
            ]

            # award points only for an accepted testcase
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

            # no time remains after a total time limit failure
            if execution_result["result"] == "TLE":
                break

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
        # remove submitted source files for every result path
        if submission_directory is not None:
            cleanup_submission_directory(
                submission_directory
            )