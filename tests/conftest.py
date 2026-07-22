from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.repositories.database as database
import app.services.backup_service as backup_service
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_directory = tmp_path / "data"
    database_path = data_directory / "oj.db"
    backup_directory = data_directory / "backups"

    monkeypatch.setattr(
        database,
        "DATA_DIR",
        data_directory,
    )
    monkeypatch.setattr(
        database,
        "DB_PATH",
        database_path,
    )
    monkeypatch.setattr(
        database,
        "BACKUP_DIR",
        backup_directory,
    )
    monkeypatch.setattr(
        backup_service,
        "DATA_DIR",
        data_directory,
    )
    monkeypatch.setattr(
        backup_service,
        "DB_PATH",
        database_path,
    )
    monkeypatch.setattr(
        backup_service,
        "BACKUP_DIR",
        backup_directory,
    )

    with TestClient(app) as test_client:
        yield test_client


def login_admin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "change-me-admin-123",
        },
    )
    assert response.status_code == 200


def sample_problem(
    problem_id: str = "P1001",
    time_limit: float = 3.0,
) -> dict:
    return {
        "id": problem_id,
        "title": "A+B Problem",
        "description": "read two integers and print their sum",
        "input_description": "two integers",
        "output_description": "one integer",
        "samples": [
            {
                "input": "1 2\n",
                "output": "3\n",
            }
        ],
        "constraints": "absolute values are at most 1000",
        "time_limit": time_limit,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": ["basic"],
        "test_cases": [
            {
                "case_id": "case_01",
                "input": "1 2\n",
                "output": "3\n",
                "score": 50,
                "is_hidden": False,
            },
            {
                "case_id": "case_02",
                "input": "-1 2\n",
                "output": "1\n",
                "score": 50,
                "is_hidden": True,
            },
        ],
    }
