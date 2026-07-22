from app.services.log_view_service import to_student_log_view
from app.utils.judge_text import (
    sanitize_error_message,
    truncate_text,
)


def test_truncation_and_path_sanitization():
    truncated = truncate_text("x" * 5000)
    assert len(truncated) < 5000
    assert truncated.endswith("...[truncated]")

    windows = sanitize_error_message(
        r'C:\oj\temp\submission_1\main.py line 3'
    )
    linux = sanitize_error_message(
        "/home/server/oj/temp/submission_1/main.py line 3"
    )
    assert "C:\\oj" not in windows
    assert "/home/server" not in linux


def test_hidden_log_view_does_not_leak_answers():
    log = {
        "id": 1,
        "submission_id": 1,
        "case_id": "case_02",
        "result": "WA",
        "score": 0,
        "maximum_score": 50,
        "time_used": 0.1,
        "memory_used": None,
        "exit_code": 0,
        "input_data": "secret input",
        "expected_output": "secret answer",
        "stdout": "wrong",
        "stderr": "",
        "message": "wrong answer",
        "is_hidden": 1,
        "created_at": "2026-07-19T00:00:00Z",
    }
    view = to_student_log_view(log)
    assert "input_data" not in view
    assert "expected_output" not in view
    assert "stdout" not in view
