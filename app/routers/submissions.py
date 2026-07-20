from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Query,
)
from fastapi.responses import JSONResponse

from app.dependencies.auth import (
    get_current_user,
    require_roles,
)
from app.models.submission import SubmissionCreate
from app.services.submission_service import (
    create_new_submission,
    get_submission_detail,
    get_submission_list,
    get_submission_logs,
    prepare_submission_rejudge,
    process_submission,
)


router = APIRouter(
    prefix="/api/submissions",
    tags=["submissions"],
)


@router.post("", status_code=202)
async def create_submission_endpoint(
    submission_data: SubmissionCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    accept source code and schedule background judging
    """

    try:
        created_submission = create_new_submission(
            user_id=current_user["id"],
            submission_data=submission_data,
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

    background_tasks.add_task(
        process_submission,
        created_submission["submission_id"],
    )

    return {
        "code": 202,
        "message": "submission accepted",
        "data": created_submission,
    }


@router.get("")
async def get_submissions_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    problem_id: str | None = Query(default=None),
    user_id: int | None = Query(default=None, gt=0),
    status: Literal[
        "pending",
        "running",
        "finished",
        "failed",
    ] | None = Query(default=None),
    result: Literal[
        "AC",
        "WA",
        "RE",
        "TLE",
        "SE",
    ] | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """
    return role restricted filtered submissions
    """

    try:
        data = get_submission_list(
            page=page,
            page_size=page_size,
            current_user=current_user,
            problem_id=problem_id,
            requested_user_id=user_id,
            status=status,
            result=result,
            start_time=start_time,
            end_time=end_time,
        )
    except PermissionError as error:
        return JSONResponse(
            status_code=403,
            content={
                "code": 403,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "ok",
        "data": data,
    }


@router.get("/{submission_id}")
async def get_submission_endpoint(
    submission_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    return one role restricted submission
    """

    try:
        submission = get_submission_detail(
            submission_id,
            current_user,
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
    except PermissionError as error:
        return JSONResponse(
            status_code=403,
            content={
                "code": 403,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "ok",
        "data": submission,
    }


@router.post("/{submission_id}/rejudge", status_code=202)
async def rejudge_submission_endpoint(
    submission_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(
        require_roles("teacher", "admin")
    ),
):
    """
    reset and schedule one completed submission
    """

    try:
        prepared = prepare_submission_rejudge(
            submission_id,
            current_user=current_user,
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
    except ValueError as error:
        return JSONResponse(
            status_code=409,
            content={
                "code": 409,
                "message": str(error),
                "data": None,
            },
        )

    background_tasks.add_task(
        process_submission,
        submission_id,
    )

    return {
        "code": 202,
        "message": "submission accepted for rejudge",
        "data": prepared,
    }


@router.get("/{submission_id}/logs")
async def get_submission_logs_endpoint(
    submission_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    return role appropriate testcase logs
    """

    try:
        data = get_submission_logs(
            submission_id,
            current_user,
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
    except PermissionError as error:
        return JSONResponse(
            status_code=403,
            content={
                "code": 403,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "ok",
        "data": data,
    }
