import json

from app.repositories.database import get_connection


def create_backup_record(
    backup_id: str,
    created_at: str,
    storage_type: str,
    file_list: list[str],
    created_by: int,
) -> None:
    """
    store metadata for one successfully created backup
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO backups (
                backup_id,
                created_at,
                storage_type,
                file_list,
                created_by
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                backup_id,
                created_at,
                storage_type,
                json.dumps(file_list),
                created_by,
            ),
        )
        connection.commit()

    finally:
        connection.close()


def list_backup_records() -> list[dict]:
    """
    return backup metadata ordered from newest to oldest
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM backups
            ORDER BY created_at DESC
            """
        ).fetchall()

        result = []

        for row in rows:
            item = dict(row)
            item["file_list"] = json.loads(
                item["file_list"]
            )
            result.append(item)

        return result

    finally:
        connection.close()


def find_backup_record(
    backup_id: str,
) -> dict | None:
    """
    return metadata for one backup id
    """

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM backups WHERE backup_id = ?",
            (backup_id,),
        ).fetchone()

        if row is None:
            return None

        result = dict(row)
        result["file_list"] = json.loads(
            result["file_list"]
        )

        return result

    finally:
        connection.close()
