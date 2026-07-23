from tests.conftest import (
    login_admin,
    login_user,
    register_user,
    sample_problem,
)


def test_problem_crud_validation_and_student_visibility(
    client,
):
    """
    check problem management and hidden testcase protection
    """

    login_admin(client)

    created = client.post(
        "/api/problems",
        json=sample_problem(),
    )

    assert created.status_code == 201

    duplicate = client.post(
        "/api/problems",
        json=sample_problem(),
    )

    assert duplicate.status_code == 409

    invalid_payload = sample_problem(
        problem_id="BAD_SCORE"
    )

    invalid_payload[
        "test_cases"
    ][0]["score"] = 40

    invalid = client.post(
        "/api/problems",
        json=invalid_payload,
    )

    assert invalid.status_code == 422

    admin_detail = client.get(
        "/api/problems/P1001"
    )

    assert admin_detail.status_code == 200
    assert len(
        admin_detail.json()["data"]["test_cases"]
    ) == 2

    update_payload = sample_problem()
    update_payload.pop("id")
    update_payload["title"] = "Updated A+B"
    update_payload["constraints"] = (
        "values are between -10 and 10"
    )

    updated = client.put(
        "/api/problems/P1001",
        json=update_payload,
    )

    assert updated.status_code == 200

    client.post(
        "/api/auth/logout"
    )

    register_user(
        client,
        "student02",
    )

    login_user(
        client,
        "student02",
    )

    student_detail = client.get(
        "/api/problems/P1001"
    )

    assert student_detail.status_code == 200
    assert (
        "test_cases"
        not in student_detail.json()["data"]
    )

    forbidden = client.delete(
        "/api/problems/P1001"
    )

    assert forbidden.status_code == 403
