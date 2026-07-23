import asyncio
from pathlib import Path

import pytest

import app.judge.evaluator as evaluator
from app.judge.comparator import compare_output
from app.judge.runner import (
    cleanup_submission_directory,
    prepare_submission_directory,
    run_test_case,
)


def test_runner_preserves_multiline_input():
    """
    check that stdin lines are preserved
    """

    directory = prepare_submission_directory(
        9001,
        (
            "count = int(input())\n"
            "numbers = list(map(int, input().split()))\n"
            "print(count)\n"
            "print(sum(numbers))\n"
        ),
    )

    try:
        result = asyncio.run(
            run_test_case(
                directory,
                "3\n10 20 30\n",
                "3\n60\n",
                2.0,
            )
        )

        assert result["result"] == "AC"

    finally:
        cleanup_submission_directory(
            directory
        )

    assert not directory.exists()


def test_each_testcase_receives_full_time_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """
    check separate time limit for every testcase
    """

    received_limits = []

    async def fake_run_test_case(
        submission_directory,
        input_data,
        expected_output,
        time_limit,
    ):
        received_limits.append(
            time_limit
        )

        return {
            "result": "AC",
            "stdout": expected_output,
            "stderr": "",
            "exit_code": 0,
            "time_used": 0.2,
            "memory_used": None,
            "message": "accepted",
        }

    monkeypatch.setattr(
        evaluator,
        "prepare_submission_directory",
        lambda submission_id, source_code: tmp_path,
    )

    monkeypatch.setattr(
        evaluator,
        "cleanup_submission_directory",
        lambda submission_directory: None,
    )

    monkeypatch.setattr(
        evaluator,
        "run_test_case",
        fake_run_test_case,
    )

    result = asyncio.run(
        evaluator.judge_solution(
            submission_id=9999,
            source_code="print('ok')",
            time_limit=1.25,
            test_cases=[
                {
                    "case_id": "case_01",
                    "input_data": "first\n",
                    "expected_output": "first\n",
                    "score": 50,
                    "is_hidden": False,
                },
                {
                    "case_id": "case_02",
                    "input_data": "second\n",
                    "expected_output": "second\n",
                    "score": 50,
                    "is_hidden": True,
                },
            ],
        )
    )

    assert received_limits == [
        1.25,
        1.25,
    ]

    assert result["result"] == "AC"
    assert result["score"] == 100
    assert result["total_time"] == pytest.approx(
        0.4
    )


def test_tle_output_comparison_and_invalid_utf8():
    """
    check timeout encoding and output comparison
    """

    assert compare_output(
        "3 \r\n\r\n",
        "3\n",
    )

    assert not compare_output(
        " answer 3\n",
        "3\n",
    )

    tle_directory = prepare_submission_directory(
        9002,
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
        cleanup_submission_directory(
            tle_directory
        )

    utf8_directory = prepare_submission_directory(
        9003,
        (
            "import sys\n"
            "sys.stdout.buffer.write(b'\\xff')\n"
        ),
    )

    try:
        utf8_result = asyncio.run(
            run_test_case(
                utf8_directory,
                "",
                "",
                2.0,
            )
        )

        assert utf8_result["result"] == "RE"

    finally:
        cleanup_submission_directory(
            utf8_directory
        )
