from tests.conftest import (
    login_admin,
    login_user,
    register_user,
)


def test_registration_login_roles_and_blocking(
    client,
):
    """
    check registration login roles and blocked accounts
    """

    student_id = register_user(
        client,
        "student01",
    )

    duplicate = client.post(
        "/api/auth/register",
        json={
            "username": "student01",
            "password": "password123",
        },
    )

    assert duplicate.status_code == 409

    login_user(
        client,
        "student01",
    )

    me = client.get(
        "/api/auth/me"
    )

    assert me.status_code == 200
    assert me.json()["data"]["role"] == "student"
    assert "password_hash" not in me.json()["data"]

    client.post(
        "/api/auth/logout"
    )

    login_admin(client)

    updated = client.put(
        f"/api/users/{student_id}",
        json={
            "role": "teacher",
            "is_active": False,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["data"]["role"] == "teacher"
    assert updated.json()["data"]["is_active"] is False

    client.post(
        "/api/auth/logout"
    )

    blocked_login = client.post(
        "/api/auth/login",
        json={
            "username": "student01",
            "password": "password123",
        },
    )

    assert blocked_login.status_code == 403
