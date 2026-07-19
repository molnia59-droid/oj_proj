from app.repositories.database import get_connection
from app.utils.time import utc_now_iso


# keep password hashes out of public user queries
PUBLIC_USER_COLUMNS = """
    id,
    username,
    role,
    is_active,
    last_seen_at,
    created_at,
    updated_at
"""


def find_by_username(username: str) -> dict | None:
    """
    return one full user row for authentication
    """

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        return dict(row) if row is not None else None

    finally:
        connection.close()


def create_user(
    username: str,
    password_hash: str,
    role: str = "student",
) -> int:
    """
    insert one enabled user and return its generated id
    """

    connection = get_connection()
    now = utc_now_iso()

    try:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                is_active,
                last_seen_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 1, NULL, ?, ?)
            """,
            (
                username,
                password_hash,
                role,
                now,
                now,
            ),
        )
        connection.commit()

        return int(cursor.lastrowid)

    finally:
        connection.close()


def find_by_id(user_id: int) -> dict | None:
    """
    return one full user row by id
    """

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        return dict(row) if row is not None else None

    finally:
        connection.close()


def find_public_by_id(user_id: int) -> dict | None:
    """
    return one user without password data
    """

    connection = get_connection()

    try:
        row = connection.execute(
            f"SELECT {PUBLIC_USER_COLUMNS} FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        return dict(row) if row is not None else None

    finally:
        connection.close()


def list_users(limit: int, offset: int) -> list[dict]:
    """
    return one page of public user rows
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            f"""
            SELECT {PUBLIC_USER_COLUMNS}
            FROM users
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_users() -> int:
    """
    return the total number of accounts
    """

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()

        return int(row["total"])

    finally:
        connection.close()


def update_user(
    user_id: int,
    role: str,
    is_active: bool,
) -> bool:
    """
    update administrator controlled account fields
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE users
            SET role = ?,
                is_active = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                role,
                int(is_active),
                utc_now_iso(),
                user_id,
            ),
        )
        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()


def touch_user_last_seen(user_id: int) -> None:
    """
    record the latest authenticated request for online presence
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE users
            SET last_seen_at = ?
            WHERE id = ?
            """,
            (
                utc_now_iso(),
                user_id,
            ),
        )
        connection.commit()

    finally:
        connection.close()


def clear_user_presence(user_id: int) -> None:
    """
    mark one user offline immediately
    """

    connection = get_connection()

    try:
        connection.execute(
            "UPDATE users SET last_seen_at = NULL WHERE id = ?",
            (user_id,),
        )
        connection.commit()

    finally:
        connection.close()


def clear_all_user_presence() -> None:
    """
    mark every user offline when the server starts or stops
    """

    connection = get_connection()

    try:
        connection.execute(
            "UPDATE users SET last_seen_at = NULL"
        )
        connection.commit()

    finally:
        connection.close()
