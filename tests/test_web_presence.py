from app.repositories.user_repository import (
    clear_all_user_presence,
    find_public_by_id,
)
from tests.conftest import login_admin


def test_online_presence_uses_last_seen(client):
    """
    confirm that authenticated requests update last seen time
    """

    login_admin(client)

    # the protected users endpoint updates the current administrator presence
    response = client.get("/api/users")
    assert response.status_code == 200

    admin = next(
        item
        for item in response.json()["data"]["items"]
        if item["username"] == "admin"
    )
    assert admin["last_seen_at"] is not None
    assert admin["is_online"] is True

    # startup and shutdown use the same operation to mark everyone offline
    clear_all_user_presence()
    stored_admin = find_public_by_id(admin["id"])
    assert stored_admin["last_seen_at"] is None


def test_main_html_pages_render(client):
    """
    confirm that the simplified server rendered pages open successfully
    """

    assert client.get("/web/login").status_code == 200
    login_admin(client)

    for path in (
        "/web/problems",
        "/web/problems/new",
        "/web/submissions",
        "/web/users",
    ):
        assert client.get(path).status_code == 200


def test_api_me_updates_presence_and_logout_clears_it(client):
    """
    confirm that api session actions keep presence accurate
    """

    login_admin(client)

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    admin_id = me.json()["data"]["id"]

    stored_admin = find_public_by_id(admin_id)
    assert stored_admin["last_seen_at"] is not None

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    stored_admin = find_public_by_id(admin_id)
    assert stored_admin["last_seen_at"] is None
