from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.repositories.database as database
import app.services.backup_service as backup_service
from app.main import app


@pytest.fixture
def client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    create an isolated database for every test
    """

    data_dir = tmp_path / "data"
    db_path = data_dir / "oj.db"
    backup_dir = data_dir / "backups"

    # redirect database paths to the pytest temporary folder
    monkeypatch.setattr(
        database,
        "DATA_DIR",
        data_dir,
    )
    monkeypatch.setattr(
        database,
        "DB_PATH",
        db_path,
    )
    monkeypatch.setattr(
        database,
        "BACKUP_DIR",
        backup_dir,
    )

    # backup service stores imported copies of these paths
    monkeypatch.setattr(
        backup_service,
        "DATA_DIR",
        data_dir,
    )
    monkeypatch.setattr(
        backup_service,
        "DB_PATH",
        db_path,
    )
    monkeypatch.setattr(
        backup_service,
        "BACKUP_DIR",
        backup_dir,
    )

    with TestClient(app) as test_client:
        yield test_client


def login_admin(
    client: TestClient,
) -> None:
    """
    authenticate the initial administrator
    """

    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "change-me-admin-123",
        },
    )

    assert response.status_code == 200


def register_user(
    client: TestClient,
    username: str,
    password: str = "password123",
) -> int:
    """
    register one student and return the user id
    """

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 201

    return int(
        response.json()["data"]["id"]
    )


def login_user(
    client: TestClient,
    username: str,
    password: str = "password123",
) -> None:
    """
    authenticate one registered user
    """

    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200


def sample_problem(
    problem_id: str = "P1001",
    time_limit: float = 1.0,
) -> dict:
    """
    create one valid problem with multiline input
    """

    return {
        "id": problem_id,
        "title": "A+B Problem",
        "description": (
            "read two integers from separate lines"
        ),
        "input_description": (
            "one integer is provided on every line"
        ),
        "output_description": "print their sum",
        "samples": [
            {
                "input": "1\n2\n",
                "output": "3\n",
            }
        ],
        "constraints": (
            "absolute values are at most 1000"
        ),
        "time_limit": time_limit,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": [
            "basic",
            "multiline",
        ],
        "test_cases": [
            {
                "case_id": "case_01",
                "input": "1\n2\n",
                "output": "3\n",
                "score": 50,
                "is_hidden": False,
            },
            {
                "case_id": "case_02",
                "input": "-1\n2\n",
                "output": "1\n",
                "score": 50,
                "is_hidden": True,
            },
        ],
    }


def submit_code(
    client: TestClient,
    source_code: str,
) -> dict:
    """
    submit code and return its final detail
    """

    response = client.post(
        "/api/submissions",
        json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": source_code,
        },
    )

    assert response.status_code == 202

    submission_id = response.json()[
        "data"
    ]["submission_id"]

    detail = client.get(
        f"/api/submissions/{submission_id}"
    )

    assert detail.status_code == 200

    return detail.json()["data"]
