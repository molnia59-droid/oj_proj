from tests.conftest import login_admin


def test_registration_login_and_user_management(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "student01",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    student_id = response.json()["data"]["id"]

    duplicate = client.post(
        "/api/auth/register",
        json={
            "username": "student01",
            "password": "password123",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["data"] is None

    login_admin(client)

    detail = client.get(f"/api/users/{student_id}")
    assert detail.status_code == 200
    assert "password_hash" not in detail.json()["data"]

    updated = client.put(
        f"/api/users/{student_id}",
        json={
            "role": "teacher",
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["role"] == "teacher"

    audit = client.get(
        "/api/audit-logs?action=UPDATE_USER_ROLE"
    )
    assert audit.status_code == 200
    assert audit.json()["data"]["total"] == 1


def test_inactive_user_cannot_login(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "blocked01",
            "password": "password123",
        },
    )
    user_id = response.json()["data"]["id"]

    login_admin(client)
    disabled = client.put(
        f"/api/users/{user_id}",
        json={
            "role": "student",
            "is_active": False,
        },
    )
    assert disabled.status_code == 200

    client.post("/api/auth/logout")
    login = client.post(
        "/api/auth/login",
        json={
            "username": "blocked01",
            "password": "password123",
        },
    )
    assert login.status_code == 403
