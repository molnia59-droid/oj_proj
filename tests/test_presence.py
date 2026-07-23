from app.repositories.database import get_connection
from app.repositories.user_repository import find_public_by_id
from tests.conftest import (
    login_admin,
    login_user,
    register_user,
)


def test_logout_preserves_last_seen_and_clears_session(
    client,
):
    """
    check that logout preserves last activity
    """

    login_admin(client)

    me = client.get(
        "/api/auth/me"
    )

    admin_id = int(
        me.json()["data"]["id"]
    )

    before = find_public_by_id(
        admin_id
    )

    assert before is not None
    assert before["last_seen_at"] is not None

    logout = client.post(
        "/api/auth/logout"
    )

    assert logout.status_code == 200

    after = find_public_by_id(
        admin_id
    )

    assert after is not None
    assert (
        after["last_seen_at"]
        == before["last_seen_at"]
    )

    unauthorized = client.get(
        "/api/auth/me"
    )

    assert unauthorized.status_code == 401


def test_online_and_offline_use_last_seen(
    client,
):
    """
    check recent and old activity states
    """

    student_id = register_user(
        client,
        "presence01",
    )

    login_user(
        client,
        "presence01",
    )

    assert client.get(
        "/api/auth/me"
    ).status_code == 200

    client.post(
        "/api/auth/logout"
    )

    login_admin(client)

    response = client.get(
        "/api/users"
    )

    student = next(
        item
        for item in response.json()["data"]["items"]
        if item["id"] == student_id
    )

    assert student["is_online"] is True

    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE users
            SET last_seen_at = ?
            WHERE id = ?
            """,
            (
                "2000-01-01T00:00:00Z",
                student_id,
            ),
        )
        connection.commit()

    finally:
        connection.close()

    response = client.get(
        "/api/users"
    )

    student = next(
        item
        for item in response.json()["data"]["items"]
        if item["id"] == student_id
    )

    assert student["is_online"] is False
