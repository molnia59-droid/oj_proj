from app.repositories.database import get_connection
from app.utils.judge_text import truncate_text
from app.utils.time import utc_now_iso


def create_submission(
    user_id: int,
    problem_id: str,
    language: str,
    source_code: str,
) -> int:
    """
    insert one pending source code submission
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO submissions (
                user_id,
                problem_id,
                language,
                source_code,
                status,
                result,
                score,
                total_time,
                created_at,
                started_at,
                finished_at
            )
            VALUES (?, ?, ?, ?, 'pending', NULL, 0, NULL, ?, NULL, NULL)
            """,
            (
                user_id,
                problem_id,
                language,
                source_code,
                utc_now_iso(),
            ),
        )
        connection.commit()

        return int(cursor.lastrowid)

    finally:
        connection.close()


def find_submission_by_id(
    submission_id: int,
) -> dict | None:
    """
    return one submission row by id
    """

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()

        return dict(row) if row is not None else None

    finally:
        connection.close()


def mark_submission_running(submission_id: int) -> bool:
    """
    apply the pending to running state transition
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'running',
                result = NULL,
                started_at = ?,
                finished_at = NULL
            WHERE id = ?
              AND status = 'pending'
            """,
            (utc_now_iso(), submission_id),
        )
        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()


def finish_submission(
    submission_id: int,
    result: str,
    score: int,
    total_time: float,
    test_results: list[dict],
) -> None:
    """
    save judge logs and finish a running submission atomically
    """

    connection = get_connection()
    created_at = utc_now_iso()

    try:
        rows = [
            (
                submission_id,
                test_result["case_id"],
                test_result["result"],
                test_result["score"],
                test_result["maximum_score"],
                test_result["time_used"],
                test_result.get("memory_used"),
                test_result["exit_code"],
                truncate_text(test_result["input_data"]),
                truncate_text(test_result["expected_output"]),
                truncate_text(test_result["stdout"]),
                truncate_text(test_result["stderr"]),
                truncate_text(test_result["message"]),
                int(test_result["is_hidden"]),
                created_at,
            )
            for test_result in test_results
        ]

        connection.executemany(
            """
            INSERT INTO test_logs (
                submission_id,
                case_id,
                result,
                score,
                maximum_score,
                time_used,
                memory_used,
                exit_code,
                input_data,
                expected_output,
                stdout,
                stderr,
                message,
                is_hidden,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'finished',
                result = ?,
                score = ?,
                total_time = ?,
                finished_at = ?
            WHERE id = ?
              AND status = 'running'
            """,
            (
                result,
                score,
                total_time,
                created_at,
                submission_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "invalid submission status transition"
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def mark_submission_failed(
    submission_id: int,
    detail: str | None = None,
) -> bool:
    """
    mark a pending or running submission as a system failure
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'failed',
                result = 'SE',
                score = 0,
                finished_at = ?
            WHERE id = ?
              AND status IN ('pending', 'running')
            """,
            (utc_now_iso(), submission_id),
        )

        if cursor.rowcount == 1 and detail:
            connection.execute(
                """
                INSERT INTO test_logs (
                    submission_id,
                    case_id,
                    result,
                    score,
                    maximum_score,
                    time_used,
                    memory_used,
                    exit_code,
                    input_data,
                    expected_output,
                    stdout,
                    stderr,
                    message,
                    is_hidden,
                    created_at
                )
                VALUES (?, 'system', 'SE', 0, 0, 0, NULL, NULL, '', '', '', '', ?, 1, ?)
                """,
                (
                    submission_id,
                    truncate_text(detail),
                    utc_now_iso(),
                ),
            )

        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()


def _build_submission_filters(
    user_id: int | None,
    problem_id: str | None,
    status: str | None,
    result: str | None,
    start_time: str | None,
    end_time: str | None,
) -> tuple[str, list]:
    """
    build parameterized filters for submission queries
    """

    conditions = []
    parameters = []

    if user_id is not None:
        conditions.append("submissions.user_id = ?")
        parameters.append(user_id)

    if problem_id is not None:
        conditions.append("submissions.problem_id = ?")
        parameters.append(problem_id)

    if status is not None:
        conditions.append("submissions.status = ?")
        parameters.append(status)

    if result is not None:
        conditions.append("submissions.result = ?")
        parameters.append(result)

    if start_time is not None:
        conditions.append("submissions.created_at >= ?")
        parameters.append(start_time)

    if end_time is not None:
        conditions.append("submissions.created_at <= ?")
        parameters.append(end_time)

    if not conditions:
        return "", parameters

    return "WHERE " + " AND ".join(conditions), parameters


def list_submissions(
    limit: int,
    offset: int,
    user_id: int | None = None,
    problem_id: str | None = None,
    status: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict]:
    """
    return one filtered page of submission summaries
    """

    where_clause, parameters = _build_submission_filters(
        user_id,
        problem_id,
        status,
        result,
        start_time,
        end_time,
    )
    parameters.extend([limit, offset])
    connection = get_connection()

    try:
        rows = connection.execute(
            f"""
            SELECT
                id,
                user_id,
                problem_id,
                language,
                status,
                result,
                score,
                total_time,
                created_at,
                started_at,
                finished_at
            FROM submissions
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_submissions(
    user_id: int | None = None,
    problem_id: str | None = None,
    status: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> int:
    """
    count submissions that match optional filters
    """

    where_clause, parameters = _build_submission_filters(
        user_id,
        problem_id,
        status,
        result,
        start_time,
        end_time,
    )
    connection = get_connection()

    try:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM submissions
            {where_clause}
            """,
            parameters,
        ).fetchone()

        return int(row["total"])

    finally:
        connection.close()


def reset_submission_for_rejudge(
    submission_id: int,
) -> bool:
    """
    clear old logs and move a completed submission to pending
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'pending',
                result = NULL,
                score = 0,
                total_time = NULL,
                started_at = NULL,
                finished_at = NULL
            WHERE id = ?
              AND status IN ('finished', 'failed')
            """,
            (submission_id,),
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return False

        connection.execute(
            "DELETE FROM test_logs WHERE submission_id = ?",
            (submission_id,),
        )
        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def list_submission_test_logs(
    submission_id: int,
) -> list[dict]:
    """
    return all testcase logs for one submission in order
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM test_logs
            WHERE submission_id = ?
            ORDER BY id
            """,
            (submission_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def _build_log_filters(
    submission_id: int | None,
    problem_id: str | None,
    user_id: int | None,
    result: str | None,
    start_time: str | None,
    end_time: str | None,
) -> tuple[str, list]:
    """
    build parameterized filters for full judge log searches
    """

    conditions = []
    parameters = []

    if submission_id is not None:
        conditions.append("test_logs.submission_id = ?")
        parameters.append(submission_id)

    if problem_id is not None:
        conditions.append("submissions.problem_id = ?")
        parameters.append(problem_id)

    if user_id is not None:
        conditions.append("submissions.user_id = ?")
        parameters.append(user_id)

    if result is not None:
        conditions.append("test_logs.result = ?")
        parameters.append(result)

    if start_time is not None:
        conditions.append("test_logs.created_at >= ?")
        parameters.append(start_time)

    if end_time is not None:
        conditions.append("test_logs.created_at <= ?")
        parameters.append(end_time)

    if not conditions:
        return "", parameters

    return "WHERE " + " AND ".join(conditions), parameters


def list_test_logs(
    limit: int,
    offset: int,
    submission_id: int | None = None,
    problem_id: str | None = None,
    user_id: int | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict]:
    """
    return one filtered page of full judge logs
    """

    where_clause, parameters = _build_log_filters(
        submission_id,
        problem_id,
        user_id,
        result,
        start_time,
        end_time,
    )
    parameters.extend([limit, offset])
    connection = get_connection()

    try:
        rows = connection.execute(
            f"""
            SELECT
                test_logs.*,
                submissions.problem_id,
                submissions.user_id
            FROM test_logs
            JOIN submissions
              ON submissions.id = test_logs.submission_id
            {where_clause}
            ORDER BY test_logs.id DESC
            LIMIT ? OFFSET ?
            """,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_test_logs(
    submission_id: int | None = None,
    problem_id: str | None = None,
    user_id: int | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> int:
    """
    count judge logs that match optional filters
    """

    where_clause, parameters = _build_log_filters(
        submission_id,
        problem_id,
        user_id,
        result,
        start_time,
        end_time,
    )
    connection = get_connection()

    try:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM test_logs
            JOIN submissions
              ON submissions.id = test_logs.submission_id
            {where_clause}
            """,
            parameters,
        ).fetchone()

        return int(row["total"])

    finally:
        connection.close()


def fail_submission_with_logs(
    submission_id: int,
    total_time: float,
    test_results: list[dict],
    detail: str | None = None,
) -> None:
    """
    save available system error logs and fail the submission
    """

    connection = get_connection()
    created_at = utc_now_iso()

    try:
        rows = [
            (
                submission_id,
                test_result["case_id"],
                test_result["result"],
                test_result["score"],
                test_result["maximum_score"],
                test_result["time_used"],
                test_result.get("memory_used"),
                test_result["exit_code"],
                truncate_text(test_result["input_data"]),
                truncate_text(test_result["expected_output"]),
                truncate_text(test_result["stdout"]),
                truncate_text(test_result["stderr"]),
                truncate_text(test_result["message"]),
                int(test_result["is_hidden"]),
                created_at,
            )
            for test_result in test_results
        ]

        if rows:
            connection.executemany(
                """
                INSERT INTO test_logs (
                    submission_id,
                    case_id,
                    result,
                    score,
                    maximum_score,
                    time_used,
                    memory_used,
                    exit_code,
                    input_data,
                    expected_output,
                    stdout,
                    stderr,
                    message,
                    is_hidden,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        elif detail:
            connection.execute(
                """
                INSERT INTO test_logs (
                    submission_id,
                    case_id,
                    result,
                    score,
                    maximum_score,
                    time_used,
                    memory_used,
                    exit_code,
                    input_data,
                    expected_output,
                    stdout,
                    stderr,
                    message,
                    is_hidden,
                    created_at
                )
                VALUES (?, 'system', 'SE', 0, 0, 0, NULL, NULL, '', '', '', '', ?, 1, ?)
                """,
                (
                    submission_id,
                    truncate_text(detail),
                    created_at,
                ),
            )

        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'failed',
                result = 'SE',
                score = 0,
                total_time = ?,
                finished_at = ?
            WHERE id = ?
              AND status IN ('pending', 'running')
            """,
            (
                total_time,
                created_at,
                submission_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "invalid submission status transition"
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
