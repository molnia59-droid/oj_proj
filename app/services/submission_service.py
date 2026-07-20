import logging

from app.judge.evaluator import judge_solution
from app.models.submission import SubmissionCreate
from app.repositories.problem_repository import (
    find_problem_by_id,
    find_problem_with_tests,
)
from app.repositories.submission_repository import (
    count_submissions,
    count_test_logs,
    create_submission,
    fail_submission_with_logs,
    find_submission_by_id,
    finish_submission,
    list_submission_test_logs,
    list_submissions,
    list_test_logs,
    mark_submission_failed,
    mark_submission_running,
    reset_submission_for_rejudge,
)
from app.services.audit_service import record_audit
from app.services.log_view_service import (
    to_student_log_view,
    to_teacher_log_view,
)


logger = logging.getLogger(__name__)


async def process_submission(submission_id: int) -> None:
    """
    move one pending submission through the complete judge workflow
    """

    # load the source code before attempting a state transition
    submission = find_submission_by_id(submission_id)

    if submission is None:
        return

    # only one worker may change pending into running
    if not mark_submission_running(submission_id):
        return

    try:
        # load the active problem together with every hidden testcase
        problem = find_problem_with_tests(
            submission["problem_id"]
        )

        if problem is None:
            raise LookupError("problem not found")

        test_cases = problem.get("test_cases", [])

        if not test_cases:
            raise ValueError("problem has no test cases")

        # execute the source outside the web request
        judge_result = await judge_solution(
            submission_id=submission_id,
            source_code=submission["source_code"],
            time_limit=float(problem["time_limit"]),
            test_cases=test_cases,
        )

        # a system error uses failed status and still preserves available logs
        if judge_result["result"] == "SE":
            fail_submission_with_logs(
                submission_id=submission_id,
                total_time=judge_result["total_time"],
                test_results=judge_result["cases"],
                detail=judge_result.get("message"),
            )
            return

        # normal verdicts finish the submission and save all test logs atomically
        finish_submission(
            submission_id=submission_id,
            result=judge_result["result"],
            score=judge_result["score"],
            total_time=judge_result["total_time"],
            test_results=judge_result["cases"],
        )

    except Exception as error:
        logger.exception(
            "submission %s failed during judging",
            submission_id,
        )

        # preserve a safe system log when failure happens outside the runner
        mark_submission_failed(
            submission_id,
            detail=f"{type(error).__name__}: {error}",
        )


def create_new_submission(
    user_id: int,
    submission_data: SubmissionCreate,
) -> dict:
    """
    create one pending submission for an active problem
    """

    if find_problem_by_id(submission_data.problem_id) is None:
        raise LookupError("problem not found")

    submission_id = create_submission(
        user_id=user_id,
        problem_id=submission_data.problem_id,
        language=submission_data.language,
        source_code=submission_data.source_code,
    )

    return {
        "submission_id": submission_id,
        "status": "pending",
    }


def get_submission_detail(
    submission_id: int,
    current_user: dict,
) -> dict:
    """
    return one submission after applying ownership rules
    """

    submission = find_submission_by_id(submission_id)

    if submission is None:
        raise LookupError("submission not found")

    # students may inspect only their own source code and result
    if (
        current_user["role"] == "student"
        and submission["user_id"] != current_user["id"]
    ):
        raise PermissionError("permission denied")

    return submission


def get_submission_list(
    page: int,
    page_size: int,
    current_user: dict,
    problem_id: str | None = None,
    requested_user_id: int | None = None,
    status: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """
    return filtered submissions with role based user restrictions
    """

    user_id = requested_user_id

    if current_user["role"] == "student":
        # a student cannot use the filter to access another account
        if (
            requested_user_id is not None
            and requested_user_id != current_user["id"]
        ):
            raise PermissionError("permission denied")

        user_id = current_user["id"]

    items = list_submissions(
        limit=page_size,
        offset=(page - 1) * page_size,
        user_id=user_id,
        problem_id=problem_id,
        status=status,
        result=result,
        start_time=start_time,
        end_time=end_time,
    )
    total = count_submissions(
        user_id=user_id,
        problem_id=problem_id,
        status=status,
        result=result,
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            total + page_size - 1
        ) // page_size,
    }


def prepare_submission_rejudge(
    submission_id: int,
    current_user: dict | None = None,
) -> dict:
    """
    reset a finished submission so it can be judged again
    """

    submission = find_submission_by_id(submission_id)

    if submission is None:
        raise LookupError("submission not found")

    if submission["status"] not in {"finished", "failed"}:
        raise ValueError(
            "only finished or failed submissions can be rejudged"
        )

    if not reset_submission_for_rejudge(submission_id):
        raise ValueError("submission state conflict")

    if current_user is not None:
        record_audit(
            operator_id=current_user["id"],
            action="REJUDGE_SUBMISSION",
            target_type="submission",
            target_id=submission_id,
        )

    return {
        "submission_id": submission_id,
        "status": "pending",
    }


def get_submission_logs(
    submission_id: int,
    current_user: dict,
) -> dict:
    """
    return role appropriate logs for one submission
    """

    submission = find_submission_by_id(submission_id)

    if submission is None:
        raise LookupError("submission not found")

    if (
        current_user["role"] == "student"
        and submission["user_id"] != current_user["id"]
    ):
        raise PermissionError("permission denied")

    test_logs = list_submission_test_logs(submission_id)

    if current_user["role"] in {"teacher", "admin"}:
        logs = [
            to_teacher_log_view(log)
            for log in test_logs
        ]

        # viewing hidden testcase data is an auditable action
        record_audit(
            operator_id=current_user["id"],
            action="VIEW_FULL_JUDGE_LOG",
            target_type="submission",
            target_id=submission_id,
        )
    else:
        logs = [
            to_student_log_view(log)
            for log in test_logs
        ]

    return {
        "submission_id": submission_id,
        "status": submission["status"],
        "result": submission["result"],
        "score": submission["score"],
        "total_time": submission["total_time"],
        "logs": logs,
    }


def get_full_log_list(
    page: int,
    page_size: int,
    current_user: dict,
    submission_id: int | None = None,
    problem_id: str | None = None,
    user_id: int | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """
    return searchable full logs for teachers and administrators
    """

    items = list_test_logs(
        limit=page_size,
        offset=(page - 1) * page_size,
        submission_id=submission_id,
        problem_id=problem_id,
        user_id=user_id,
        result=result,
        start_time=start_time,
        end_time=end_time,
    )
    total = count_test_logs(
        submission_id=submission_id,
        problem_id=problem_id,
        user_id=user_id,
        result=result,
        start_time=start_time,
        end_time=end_time,
    )

    # every full log search can reveal hidden testcase data
    record_audit(
        operator_id=current_user["id"],
        action="VIEW_FULL_JUDGE_LOG",
        target_type="judge_log_search",
        target_id=submission_id,
        detail=(
            f"problem_id={problem_id}, user_id={user_id}, "
            f"result={result}, start_time={start_time}, "
            f"end_time={end_time}"
        ),
    )

    return {
        "items": [
            to_teacher_log_view(item)
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            total + page_size - 1
        ) // page_size,
    }
