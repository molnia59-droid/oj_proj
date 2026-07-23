import json

import app.services.backup_service as backup_service
from tests.conftest import (
    login_admin,
    sample_problem,
)


def test_backup_create_list_and_restore(
    client,
):
    """
    check the complete valid backup workflow
    """

    login_admin(client)

    client.post(
        "/api/problems",
        json=sample_problem(),
    )

    created = client.post(
        "/api/admin/backups"
    )

    assert created.status_code == 201

    backup_id = created.json()[
        "data"
    ]["backup_id"]

    backup_dir = (
        backup_service.BACKUP_DIR
        / backup_id
    )

    assert (
        backup_dir / "oj.db"
    ).is_file()

    assert (
        backup_dir / "manifest.json"
    ).is_file()

    listed = client.get(
        "/api/admin/backups"
    )

    assert listed.status_code == 200

    assert any(
        item["backup_id"] == backup_id
        for item in listed.json()["data"]["items"]
    )

    deleted = client.delete(
        "/api/problems/P1001"
    )

    assert deleted.status_code == 200

    assert client.get(
        "/api/problems/P1001"
    ).status_code == 404

    restored = client.post(
        f"/api/admin/backups/{backup_id}/restore"
    )

    assert restored.status_code == 200

    assert client.get(
        "/api/problems/P1001"
    ).status_code == 200


def test_corrupted_backup_does_not_replace_database(
    client,
):
    """
    check restore safety for damaged sqlite data
    """

    login_admin(client)

    client.post(
        "/api/problems",
        json=sample_problem(),
    )

    created = client.post(
        "/api/admin/backups"
    )

    backup_id = created.json()[
        "data"
    ]["backup_id"]

    backup_db = (
        backup_service.BACKUP_DIR
        / backup_id
        / "oj.db"
    )

    backup_db.write_bytes(
        b"not a sqlite database"
    )

    client.post(
        "/api/problems",
        json=sample_problem(
            problem_id="P2002"
        ),
    )

    restored = client.post(
        f"/api/admin/backups/{backup_id}/restore"
    )

    assert restored.status_code == 400

    assert client.get(
        "/api/problems/P2002"
    ).status_code == 200


def test_manifest_id_must_match_directory(
    client,
):
    """
    check backup manifest identity
    """

    login_admin(client)

    created = client.post(
        "/api/admin/backups"
    )

    backup_id = created.json()[
        "data"
    ]["backup_id"]

    manifest_path = (
        backup_service.BACKUP_DIR
        / backup_id
        / "manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest["backup_id"] = (
        "different_backup_id"
    )

    manifest_path.write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    restore = client.post(
        f"/api/admin/backups/{backup_id}/restore"
    )

    assert restore.status_code == 400
