from tests.conftest import (
    login_admin,
    sample_problem,
)


def test_main_html_pages_and_multiline_form(
    client,
):
    """
    check main html pages and textarea fields
    """

    login_admin(client)

    client.post(
        "/api/problems",
        json=sample_problem(),
    )

    for path in (
        "/web/problems",
        "/web/problems/new",
        "/web/problems/P1001",
        "/web/problems/P1001/edit",
        "/web/submissions",
        "/web/users",
    ):
        response = client.get(path)
        assert response.status_code == 200

    form_page = client.get(
        "/web/problems/new"
    )

    assert (
        'name="test_input"'
        in form_page.text
    )

    assert (
        'name="test_output"'
        in form_page.text
    )

    assert "<textarea" in form_page.text
