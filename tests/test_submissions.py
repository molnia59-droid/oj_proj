from tests.conftest import (
    login_admin,
    sample_problem,
    submit_code,
)


def test_ac_wa_re_and_partial_score(
    client,
):
    """
    check main judge results
    """

    login_admin(client)

    created = client.post(
        "/api/problems",
        json=sample_problem(),
    )

    assert created.status_code == 201

    accepted = submit_code(
        client,
        (
            "a = int(input())\n"
            "b = int(input())\n"
            "print(a + b)\n"
        ),
    )

    assert accepted["result"] == "AC"
    assert accepted["score"] == 100

    wrong = submit_code(
        client,
        "print(0)\n",
    )

    assert wrong["result"] == "WA"
    assert wrong["score"] == 0

    runtime_error = submit_code(
        client,
        "print(1 / 0)\n",
    )

    assert runtime_error["result"] == "RE"
    assert runtime_error["score"] == 0

    partial = submit_code(
        client,
        (
            "a = int(input())\n"
            "b = int(input())\n"
            "print(a + b if a > 0 else 0)\n"
        ),
    )

    assert partial["result"] == "WA"
    assert partial["score"] == 50
