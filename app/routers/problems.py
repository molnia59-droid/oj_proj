from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies.auth import (
    get_current_user,
    require_roles,
)
from app.models.problem import ProblemCreate, ProblemUpdate
from app.services.problem_service import (
    create_new_problem,
    delete_existing_problem,
    get_problem_detail,
    get_problem_list,
    update_existing_problem,
)


router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.post("", status_code=201)
async def create_problem_endpoint(
    problem: ProblemCreate,
    _current_user: dict = Depends(
        require_roles("teacher", "admin")
    ),
):
    """
    create a validated problem for teacher or administrator
    """

    try:
        created_problem = create_new_problem(problem)
    except ValueError as error:
        return JSONResponse(
            status_code=409,
            content={
                "code": 409,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 201,
        "message": "problem created",
        "data": created_problem,
    }


@router.get("")
async def get_problems_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _current_user: dict = Depends(get_current_user),
):
    """
    return a paginated problem list
    """

    return {
        "code": 200,
        "message": "ok",
        "data": get_problem_list(page, page_size),
    }


@router.get("/{problem_id}")
async def get_problem_endpoint(
    problem_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    return one problem with role appropriate testcase data
    """

    problem = get_problem_detail(
        problem_id,
        include_tests=current_user["role"] in {
            "teacher",
            "admin",
        },
    )

    if problem is None:
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": "problem not found",
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "ok",
        "data": problem,
    }


@router.put("/{problem_id}")
async def update_problem_endpoint(
    problem_id: str,
    problem: ProblemUpdate,
    _current_user: dict = Depends(
        require_roles("teacher", "admin")
    ),
):
    """
    replace one existing problem configuration
    """

    try:
        updated_problem = update_existing_problem(
            problem_id,
            problem,
        )
    except LookupError as error:
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "problem updated",
        "data": updated_problem,
    }


@router.delete("/{problem_id}")
async def delete_problem_endpoint(
    problem_id: str,
    _current_user: dict = Depends(
        require_roles("teacher", "admin")
    ),
):
    """
    soft delete one problem
    """

    try:
        delete_existing_problem(problem_id)
    except LookupError as error:
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "problem deleted",
        "data": None,
    }
