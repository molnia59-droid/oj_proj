from app.utils.judge_text import (
    sanitize_error_message,
    truncate_text,
)


def to_teacher_log_view(test_log: dict) -> dict:
    """
    return a complete length limited testcase log
    """

    result = dict(test_log)
    result["is_hidden"] = bool(result["is_hidden"])
    result["memory_used"] = result.get("memory_used")

    for field in (
        "input_data",
        "expected_output",
        "stdout",
        "stderr",
        "message",
    ):
        result[field] = truncate_text(result.get(field))

    result["time_ms"] = float(
        result.get("time_used", 0)
    ) * 1000
    result["maximum_score"] = result.get(
        "maximum_score",
        0,
    )

    return result


def to_student_log_view(test_log: dict) -> dict:
    """
    remove hidden testcase data and sanitize server paths
    """

    is_hidden = bool(test_log["is_hidden"])
    result = {
        "id": test_log["id"],
        "submission_id": test_log["submission_id"],
        "case_id": test_log["case_id"],
        "result": test_log["result"],
        "score": test_log["score"],
        "maximum_score": test_log["maximum_score"],
        "time_used": test_log["time_used"],
        "time_ms": float(test_log["time_used"]) * 1000,
        "memory_used": test_log.get("memory_used"),
        "exit_code": test_log.get("exit_code"),
        "stderr": sanitize_error_message(
            truncate_text(test_log.get("stderr"))
        ),
        "message": sanitize_error_message(
            truncate_text(test_log.get("message"))
        ),
        "is_hidden": is_hidden,
        "created_at": test_log.get("created_at"),
    }

    if not is_hidden:
        result["stdout"] = truncate_text(
            test_log.get("stdout")
        )
        result["expected_output"] = truncate_text(
            test_log.get("expected_output")
        )

    return result
