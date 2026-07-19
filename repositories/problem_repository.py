import json

from app.models.problem import ProblemCreate, ProblemUpdate
from app.repositories.database import get_connection
from app.utils.time import utc_now_iso


def _serialize_samples(problem: ProblemCreate | ProblemUpdate) -> str:
    """
    convert validated sample models into json text for sqlite
    """

    return json.dumps(
        [sample.model_dump() for sample in problem.samples],
        ensure_ascii=False,
    )


def _serialize_tags(tags: list[str]) -> str:
    """
    convert the tag list into json text for sqlite
    """

    return json.dumps(tags, ensure_ascii=False)


def create_problem(problem: ProblemCreate) -> str:
    """
    insert one problem and all of its testcases in one transaction
    """

    connection = get_connection()
    now = utc_now_iso()

    try:
        connection.execute(
            """
            INSERT INTO problems (
                id,
                title,
                description,
                input_description,
                output_description,
                samples,
                constraints_text,
                time_limit,
                memory_limit,
                difficulty,
                tags,
                is_deleted,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                problem.id,
                problem.title,
                problem.description,
                problem.input_description,
                problem.output_description,
                _serialize_samples(problem),
                problem.constraints,
                problem.time_limit,
                problem.memory_limit,
                problem.difficulty.value,
                _serialize_tags(problem.tags),
                now,
                now,
            ),
        )

        rows = [
            (
                problem.id,
                test_case.case_id,
                test_case.input,
                test_case.output,
                test_case.score,
                int(test_case.is_hidden),
            )
            for test_case in problem.test_cases
        ]

        connection.executemany(
            """
            INSERT INTO test_cases (
                problem_id,
                case_id,
                input_data,
                expected_output,
                score,
                is_hidden
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

        return problem.id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def find_problem_by_id(
    problem_id: str,
    include_deleted: bool = False,
) -> dict | None:
    """
    return one problem row with optional deleted record access
    """

    connection = get_connection()

    try:
        query = "SELECT * FROM problems WHERE id = ?"

        if not include_deleted:
            query += " AND is_deleted = 0"

        row = connection.execute(
            query,
            (problem_id,),
        ).fetchone()

        return dict(row) if row is not None else None

    finally:
        connection.close()


def list_problems(limit: int, offset: int) -> list[dict]:
    """
    return one page of active problem summaries
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                title,
                difficulty,
                tags,
                time_limit,
                memory_limit,
                created_at,
                updated_at
            FROM problems
            WHERE is_deleted = 0
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_problems() -> int:
    """
    count active problems
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM problems
            WHERE is_deleted = 0
            """
        ).fetchone()

        return int(row["total"])

    finally:
        connection.close()


def find_problem_with_tests(
    problem_id: str,
) -> dict | None:
    """
    return one active problem together with all judge tests
    """

    connection = get_connection()

    try:
        problem_row = connection.execute(
            """
            SELECT *
            FROM problems
            WHERE id = ?
              AND is_deleted = 0
            """,
            (problem_id,),
        ).fetchone()

        if problem_row is None:
            return None

        test_rows = connection.execute(
            """
            SELECT
                case_id,
                input_data,
                expected_output,
                score,
                is_hidden
            FROM test_cases
            WHERE problem_id = ?
            ORDER BY id
            """,
            (problem_id,),
        ).fetchall()

        result = dict(problem_row)
        result["test_cases"] = [
            dict(row)
            for row in test_rows
        ]

        return result

    finally:
        connection.close()


def update_problem(
    problem_id: str,
    problem: ProblemUpdate,
) -> None:
    """
    replace problem fields and testcase configuration atomically
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE problems
            SET title = ?,
                description = ?,
                input_description = ?,
                output_description = ?,
                samples = ?,
                constraints_text = ?,
                time_limit = ?,
                memory_limit = ?,
                difficulty = ?,
                tags = ?,
                updated_at = ?
            WHERE id = ?
              AND is_deleted = 0
            """,
            (
                problem.title,
                problem.description,
                problem.input_description,
                problem.output_description,
                _serialize_samples(problem),
                problem.constraints,
                problem.time_limit,
                problem.memory_limit,
                problem.difficulty.value,
                _serialize_tags(problem.tags),
                utc_now_iso(),
                problem_id,
            ),
        )

        if cursor.rowcount != 1:
            raise LookupError("problem not found")

        connection.execute(
            "DELETE FROM test_cases WHERE problem_id = ?",
            (problem_id,),
        )

        rows = [
            (
                problem_id,
                test_case.case_id,
                test_case.input,
                test_case.output,
                test_case.score,
                int(test_case.is_hidden),
            )
            for test_case in problem.test_cases
        ]

        connection.executemany(
            """
            INSERT INTO test_cases (
                problem_id,
                case_id,
                input_data,
                expected_output,
                score,
                is_hidden
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def soft_delete_problem(problem_id: str) -> bool:
    """
    hide one problem without removing historical submissions
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE problems
            SET is_deleted = 1,
                updated_at = ?
            WHERE id = ?
              AND is_deleted = 0
            """,
            (utc_now_iso(), problem_id),
        )
        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()
