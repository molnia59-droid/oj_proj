import json
import os
import re
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.repositories.backup_repository import (
    create_backup_record,
    find_backup_record,
    list_backup_records,
)
from app.repositories.database import (
    BACKUP_DIR,
    DATA_DIR,
    DB_PATH,
    get_connection,
    init_db,
)
from app.repositories.user_repository import find_by_id
from app.services.audit_service import record_audit
from app.utils.time import utc_now_iso


BACKUP_ID_PATTERN = re.compile(
    r"^backup_[0-9]{8}_[0-9]{6}_[a-f0-9]{8}$"
)


def _copy_database(destination: Path) -> None:
    """
    copy sqlite consistently through the sqlite backup api
    """

    source_connection = get_connection()
    destination_connection = sqlite3.connect(destination)

    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _validate_database(database_path: Path) -> None:
    """
    reject a database file that fails sqlite integrity checking
    """

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if row is None or row[0] != "ok":
            raise ValueError("backup database is corrupted")
    except sqlite3.DatabaseError as error:
        raise ValueError(
            "backup database is corrupted"
        ) from error
    finally:
        connection.close()


def _load_manifest(
    backup_directory: Path,
    expected_backup_id: str,
) -> dict:
    """
    load and validate required backup files and metadata
    """

    manifest_path = backup_directory / "manifest.json"
    database_path = backup_directory / "oj.db"

    if not manifest_path.is_file() or not database_path.is_file():
        raise ValueError("backup files are incomplete")

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("backup manifest is invalid") from error

    if manifest.get("backup_id") != expected_backup_id:
        raise ValueError("backup manifest id does not match")

    if manifest.get("storage_type") != "sqlite":
        raise ValueError("unsupported backup storage type")

    file_list = manifest.get("files")

    if (
        not isinstance(file_list, list)
        or "oj.db" not in file_list
        or "manifest.json" not in file_list
    ):
        raise ValueError("backup manifest is incomplete")

    _validate_database(database_path)

    return manifest


def create_backup(current_user: dict) -> dict:
    """
    create database and manifest files in an atomic backup directory
    """

    created_at = utc_now_iso()
    timestamp = created_at.replace("-", "").replace(
        ":",
        "",
    ).replace("T", "_").replace("Z", "")
    backup_id = (
        f"backup_{timestamp}_{uuid4().hex[:8]}"
    )
    temporary_directory = BACKUP_DIR / (
        f".{backup_id}.tmp"
    )
    final_directory = BACKUP_DIR / backup_id

    try:
        temporary_directory.mkdir(
            parents=True,
            exist_ok=False,
        )
        database_path = temporary_directory / "oj.db"
        _copy_database(database_path)
        _validate_database(database_path)

        manifest = {
            "backup_id": backup_id,
            "created_at": created_at,
            "storage_type": "sqlite",
            "files": ["oj.db", "manifest.json"],
        }
        (temporary_directory / "manifest.json").write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporary_directory, final_directory)

        create_backup_record(
            backup_id=backup_id,
            created_at=created_at,
            storage_type="sqlite",
            file_list=manifest["files"],
            created_by=current_user["id"],
        )
        record_audit(
            operator_id=current_user["id"],
            action="CREATE_BACKUP",
            target_type="backup",
            target_id=backup_id,
        )

        return {
            "backup_id": backup_id,
            "created_at": created_at,
        }

    except Exception as error:
        if temporary_directory.exists():
            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )

        record_audit(
            operator_id=current_user["id"],
            action="CREATE_BACKUP",
            target_type="backup",
            target_id=backup_id,
            success=False,
            detail=str(error),
        )
        raise


def get_backup_list() -> dict:
    """
    return backup metadata in the shared pagination structure
    """

    items = list_backup_records()

    total = len(items)

    return {
        "items": items,
        "total": total,
        "page": 1,
        "page_size": max(total, 1),
        "total_pages": 1 if total else 0,
    }


def restore_backup(
    backup_id: str,
    current_user: dict,
) -> dict:
    """
    replace the working database with a validated backup safely
    """

    if not BACKUP_ID_PATTERN.fullmatch(backup_id):
        raise LookupError("backup not found")

    backup_directory = BACKUP_DIR / backup_id

    if (
        not backup_directory.is_dir()
        or find_backup_record(backup_id) is None
    ):
        raise LookupError("backup not found")

    safety_path = DATA_DIR / (
        f".restore_safety_{uuid4().hex}.db"
    )
    candidate_path = DATA_DIR / (
        f".restore_candidate_{uuid4().hex}.db"
    )
    replaced = False

    try:
        manifest = _load_manifest(
            backup_directory,
            expected_backup_id=backup_id,
        )
        _copy_database(safety_path)
        shutil.copy2(
            backup_directory / "oj.db",
            candidate_path,
        )
        _validate_database(candidate_path)

        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(DB_PATH) + suffix)

            if sidecar.exists():
                sidecar.unlink()

        os.replace(candidate_path, DB_PATH)
        replaced = True
        init_db()

        operator_id = (
            current_user["id"]
            if find_by_id(current_user["id"]) is not None
            else None
        )

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT OR IGNORE INTO backups (
                    backup_id,
                    created_at,
                    storage_type,
                    file_list,
                    created_by
                )
                VALUES (?, ?, 'sqlite', ?, NULL)
                """,
                (
                    backup_id,
                    manifest["created_at"],
                    json.dumps(manifest["files"]),
                ),
            )
            connection.commit()
        finally:
            connection.close()

        record_audit(
            operator_id=operator_id,
            action="RESTORE_BACKUP",
            target_type="backup",
            target_id=backup_id,
        )

        return {
            "backup_id": backup_id,
            "restored_at": utc_now_iso(),
        }

    except Exception as error:
        if replaced and safety_path.exists():
            os.replace(safety_path, DB_PATH)
            init_db()

        operator_id = (
            current_user["id"]
            if find_by_id(current_user["id"]) is not None
            else None
        )
        record_audit(
            operator_id=operator_id,
            action="RESTORE_BACKUP",
            target_type="backup",
            target_id=backup_id,
            success=False,
            detail=str(error),
        )
        raise

    finally:
        for path in (safety_path, candidate_path):
            if path.exists():
                path.unlink()
