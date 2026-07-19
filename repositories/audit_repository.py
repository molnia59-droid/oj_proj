from app.repositories.database import get_connection
from app.utils.time import utc_now_iso


def create_audit_log(
    operator_id: int | None,
    action: str,
    target_type: str,
    target_id: str | int | None,
    success: bool,
    detail: str | None = None,
) -> int:
    """
    insert one immutable administrative action record
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO audit_logs (
                operator_id,
                action,
                target_type,
                target_id,
                success,
                detail,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                operator_id,
                action,
                target_type,
                None if target_id is None else str(target_id),
                int(success),
                detail,
                utc_now_iso(),
            ),
        )
        connection.commit()

        return int(cursor.lastrowid)

    finally:
        connection.close()


def _build_filters(
    operator_id: int | None,
    action: str | None,
    target_id: str | None,
    start_time: str | None,
    end_time: str | None,
) -> tuple[str, list]:
    """
    build a parameterized where clause for optional audit filters
    """

    conditions = []
    parameters = []

    if operator_id is not None:
        conditions.append("operator_id = ?")
        parameters.append(operator_id)

    if action is not None:
        conditions.append("action = ?")
        parameters.append(action)

    if target_id is not None:
        conditions.append("target_id = ?")
        parameters.append(target_id)

    if start_time is not None:
        conditions.append("created_at >= ?")
        parameters.append(start_time)

    if end_time is not None:
        conditions.append("created_at <= ?")
        parameters.append(end_time)

    if not conditions:
        return "", parameters

    return "WHERE " + " AND ".join(conditions), parameters


def list_audit_logs(
    limit: int,
    offset: int,
    operator_id: int | None = None,
    action: str | None = None,
    target_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict]:
    """
    return one filtered page of audit records
    """

    where_clause, parameters = _build_filters(
        operator_id,
        action,
        target_id,
        start_time,
        end_time,
    )
    parameters.extend([limit, offset])
    connection = get_connection()

    try:
        rows = connection.execute(
            f"""
            SELECT *
            FROM audit_logs
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_audit_logs(
    operator_id: int | None = None,
    action: str | None = None,
    target_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> int:
    """
    count audit records that match optional filters
    """

    where_clause, parameters = _build_filters(
        operator_id,
        action,
        target_id,
        start_time,
        end_time,
    )
    connection = get_connection()

    try:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM audit_logs
            {where_clause}
            """,
            parameters,
        ).fetchone()

        return int(row["total"])

    finally:
        connection.close()
