import json

from app.models.problem import ProblemCreate, ProblemUpdate
from app.repositories.problem_repository import (
    count_problems,
    create_problem,
    find_problem_by_id,
    find_problem_with_tests,
    list_problems,
    soft_delete_problem,
    update_problem,
)


def _parse_json_list(value: str) -> list:
    """
    decode one json list stored in sqlite
    """

    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []

    return parsed if isinstance(parsed, list) else []


def _prepare_problem(
    problem: dict,
    include_tests: bool,
) -> dict:
    """
    convert one database row into the public api structure
    """

    result = dict(problem)

    # decode list fields that are stored as json text in sqlite
    result["samples"] = _parse_json_list(
        result.pop("samples")
    )
    result["tags"] = _parse_json_list(
        result.pop("tags")
    )
    result["constraints"] = result.pop(
        "constraints_text",
        "",
    )

    if "test_cases" in result:
        # expose consistent api names instead of internal column names
        result["test_cases"] = [
            {
                "case_id": test_case["case_id"],
                "input": test_case["input_data"],
                "output": test_case["expected_output"],
                "score": test_case["score"],
                "is_hidden": bool(
                    test_case["is_hidden"]
                ),
            }
            for test_case in result["test_cases"]
        ]

    # students receive no testcase configuration at all
    if not include_tests:
        result.pop("test_cases", None)

    # soft deletion is an internal persistence detail
    result.pop("is_deleted", None)

    return result


def create_new_problem(problem: ProblemCreate) -> dict:
    """
    create a problem after checking id uniqueness
    """

    if find_problem_by_id(
        problem.id,
        include_deleted=True,
    ) is not None:
        raise ValueError("problem id already exists")

    create_problem(problem)

    created = get_problem_detail(
        problem.id,
        include_tests=True,
    )

    if created is None:
        raise RuntimeError(
            "created problem could not be loaded"
        )

    return created


def get_problem_list(page: int, page_size: int) -> dict:
    """
    return one page of active problems
    """

    rows = list_problems(
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    items = []

    for row in rows:
        item = dict(row)
        item["tags"] = _parse_json_list(item["tags"])
        items.append(item)

    total = count_problems()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            total + page_size - 1
        ) // page_size,
    }


def get_problem_detail(
    problem_id: str,
    include_tests: bool,
) -> dict | None:
    """
    return one active problem with role appropriate data
    """

    problem = find_problem_with_tests(problem_id)

    if problem is None:
        return None

    return _prepare_problem(problem, include_tests)


def update_existing_problem(
    problem_id: str,
    problem: ProblemUpdate,
) -> dict:
    """
    replace editable problem data and testcase configuration
    """

    if find_problem_by_id(problem_id) is None:
        raise LookupError("problem not found")

    update_problem(problem_id, problem)
    updated = get_problem_detail(
        problem_id,
        include_tests=True,
    )

    if updated is None:
        raise LookupError("problem not found")

    return updated


def delete_existing_problem(problem_id: str) -> None:
    """
    hide one problem from active lists with soft deletion
    """

    if not soft_delete_problem(problem_id):
        raise LookupError("problem not found")
