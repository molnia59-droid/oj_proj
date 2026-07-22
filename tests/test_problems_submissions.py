from tests.conftest import login_admin, sample_problem


def test_problem_crud_and_student_visibility(client):
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

    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={
            "username": "student01",
            "password": "password123",
        },
    )
    client.post(
        "/api/auth/login",
        json={
            "username": "student01",
            "password": "password123",
        },
    )

    detail = client.get("/api/problems/P1001")
    assert detail.status_code == 200
    assert "test_cases" not in detail.json()["data"]

    forbidden = client.delete("/api/problems/P1001")
    assert forbidden.status_code == 403


def test_ac_wa_re_and_logs(client):
    login_admin(client)
    client.post("/api/problems", json=sample_problem())

    cases = [
        (
            "a, b = map(int, input().split())\nprint(a + b)",
            "AC",
            100,
        ),
        ("print(0)", "WA", 0),
        ("print(1 / 0)", "RE", 0),
    ]

    for source_code, expected_result, expected_score in cases:
        response = client.post(
            "/api/submissions",
            json={
                "problem_id": "P1001",
                "language": "python",
                "source_code": source_code,
            },
        )
        assert response.status_code == 202
        submission_id = response.json()["data"][
            "submission_id"
        ]
        detail = client.get(
            f"/api/submissions/{submission_id}"
        ).json()["data"]
        assert detail["status"] == "finished"
        assert detail["result"] == expected_result
        assert detail["score"] == expected_score

    logs = client.get(
        f"/api/submissions/{submission_id}/logs"
    )
    assert logs.status_code == 200
    assert logs.json()["data"]["logs"]

    audit = client.get(
        "/api/audit-logs?action=VIEW_FULL_JUDGE_LOG"
    )
    assert audit.json()["data"]["total"] == 1

    full_search = client.get("/api/logs")
    assert full_search.status_code == 200

    audit = client.get(
        "/api/audit-logs?action=VIEW_FULL_JUDGE_LOG"
    )
    assert audit.json()["data"]["total"] == 2


def test_web_problem_edit_preserves_constraints(client):
    """
    confirm that the html form edits the complete problem model
    """

    login_admin(client)
    created = client.post(
        "/api/problems",
        json=sample_problem(),
    )
    assert created.status_code == 201

    edit_page = client.get("/web/problems/P1001/edit")
    assert edit_page.status_code == 200
    assert "absolute values are at most 1000" in edit_page.text

    updated = client.post(
        "/web/problems/P1001/edit",
        data={
            "title": "A+B Updated",
            "description": "updated description",
            "input_description": "two integers",
            "output_description": "one integer",
            "constraints": "values are between -10 and 10",
            "time_limit": "2.0",
            "memory_limit": "128",
            "difficulty": "easy",
            "tags": "basic, math",
            "score_mode": "manual",
            "sample_input": "1 2\n",
            "sample_output": "3\n",
            "test_case_id": ["case_01", "case_02"],
            "test_input": ["1 2\n", "-1 2\n"],
            "test_output": ["3\n", "1\n"],
            "test_score": ["50", "50"],
            "test_hidden": ["0", "1"],
        },
        follow_redirects=False,
    )
    assert updated.status_code == 303

    detail = client.get("/api/problems/P1001")
    assert detail.status_code == 200
    assert (
        detail.json()["data"]["constraints"]
        == "values are between -10 and 10"
    )
