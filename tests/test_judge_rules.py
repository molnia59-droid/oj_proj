import asyncio

from app.judge.comparator import compare_output
from app.judge.evaluator import choose_overall_result
from app.judge.runner import (
    cleanup_submission_directory,
    prepare_submission_directory,
    run_test_case,
)


def test_output_comparison_and_result_priority():
    assert compare_output("3 \r\n\r\n", "3\n")
    assert not compare_output(" answer 3\n", "3\n")

    assert choose_overall_result([
        {"result": "WA"},
        {"result": "RE"},
        {"result": "TLE"},
    ]) == "TLE"
    assert choose_overall_result([
        {"result": "WA"},
        {"result": "SE"},
    ]) == "SE"


def test_tle_and_invalid_utf8_are_detected():
    tle_directory = prepare_submission_directory(
        9001,
        "while True:\n    pass\n",
    )

    try:
        tle_result = asyncio.run(
            run_test_case(
                tle_directory,
                "",
                "",
                0.1,
            )
        )
        assert tle_result["result"] == "TLE"
    finally:
        cleanup_submission_directory(tle_directory)

    utf8_directory = prepare_submission_directory(
        9002,
        "import sys\nsys.stdout.buffer.write(b'\\xff')\n",
    )

    try:
        utf8_result = asyncio.run(
            run_test_case(
                utf8_directory,
                "",
                "",
                3.0,
            )
        )
        assert utf8_result["result"] == "RE"
    finally:
        cleanup_submission_directory(utf8_directory)

def test_time_limit_is_shared_between_tests(
    monkeypatch,
):
    """
    verify that tests share one total time limit
    """

    from app.judge.evaluator import (
        judge_solution,
    )

    received_limits = []

    async def fake_run_test_case(
        submission_directory,
        input_data,
        expected_output,
        time_limit,
    ):
        received_limits.append(time_limit)

        if len(received_limits) == 1:
            return {
                "result": "AC",
                "stdout": "ok\n",
                "stderr": "",
                "exit_code": 0,
                "time_used": 0.6,
                "memory_used": None,
                "message": "accepted",
            }

        return {
            "result": "TLE",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "time_used": time_limit,
            "memory_used": None,
            "message": "time limit exceeded",
        }

    monkeypatch.setattr(
        "app.judge.evaluator.run_test_case",
        fake_run_test_case,
    )

    test_cases = [
        {
            "case_id": "case_1",
            "input_data": "",
            "expected_output": "ok\n",
            "score": 50,
            "is_hidden": False,
        },
        {
            "case_id": "case_2",
            "input_data": "",
            "expected_output": "ok\n",
            "score": 50,
            "is_hidden": True,
        },
    ]

    result = asyncio.run(
        judge_solution(
            submission_id=9999,
            source_code="print('ok')",
            time_limit=1.0,
            test_cases=test_cases,
        )
    )

    assert result["result"] == "TLE"
    assert result["score"] == 50

    assert received_limits[0] == 1.0

    assert 0.39 <= received_limits[1] <= 0.41