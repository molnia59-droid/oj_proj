from tests.conftest import login_admin, sample_problem


def test_backup_and_restore(client):
    login_admin(client)
    client.post("/api/problems", json=sample_problem())

    created = client.post("/api/admin/backups")
    assert created.status_code == 201
    backup_id = created.json()["data"]["backup_id"]

    deleted = client.delete("/api/problems/P1001")
    assert deleted.status_code == 200
    assert client.get("/api/problems/P1001").status_code == 404

    restored = client.post(
        f"/api/admin/backups/{backup_id}/restore"
    )
    assert restored.status_code == 200
    assert client.get("/api/problems/P1001").status_code == 200


def test_corrupted_backup_does_not_replace_database(
    client,
):
    from app.services import backup_service

    login_admin(client)
    client.post("/api/problems", json=sample_problem())

    created = client.post("/api/admin/backups")
    backup_id = created.json()["data"]["backup_id"]
    backup_database = (
        backup_service.BACKUP_DIR
        / backup_id
        / "oj.db"
    )
    backup_database.write_bytes(b"not a sqlite database")

    second_problem = sample_problem(problem_id="P2002")
    client.post("/api/problems", json=second_problem)

    restored = client.post(
        f"/api/admin/backups/{backup_id}/restore"
    )

    assert restored.status_code == 400
    assert client.get("/api/problems/P2002").status_code == 200


def test_backup_manifest_id_must_match_directory(client):
    """
    reject a backup whose manifest claims a different id
    """

    import json

    from app.services import backup_service

    login_admin(client)
    created = client.post("/api/admin/backups")
    backup_id = created.json()["data"]["backup_id"]
    manifest_path = (
        backup_service.BACKUP_DIR
        / backup_id
        / "manifest.json"
    )
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    manifest["backup_id"] = "backup_20000101_000000_deadbeef"
    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    restored = client.post(
        f"/api/admin/backups/{backup_id}/restore"
    )
    assert restored.status_code == 400
