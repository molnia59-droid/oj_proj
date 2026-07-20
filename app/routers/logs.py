from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import require_roles
from app.services.audit_service import get_audit_log_list
from app.services.submission_service import get_full_log_list


router = APIRouter(tags=["logs"])


@router.get("/api/logs")
async def get_logs_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    submission_id: int | None = Query(default=None, gt=0),
    problem_id: str | None = Query(default=None),
    user_id: int | None = Query(default=None, gt=0),
    result: Literal[
        "AC",
        "WA",
        "RE",
        "TLE",
        "SE",
    ] | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    current_user: dict = Depends(
        require_roles("teacher", "admin")
    ),
):
    """
    return searchable full judge logs to authorized staff
    """

    return {
        "code": 200,
        "message": "ok",
        "data": get_full_log_list(
            page=page,
            page_size=page_size,
            current_user=current_user,
            submission_id=submission_id,
            problem_id=problem_id,
            user_id=user_id,
            result=result,
            start_time=start_time,
            end_time=end_time,
        ),
    }


@router.get("/api/audit-logs")
async def get_audit_logs_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    operator_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    _current_user: dict = Depends(require_roles("admin")),
):
    """
    return searchable audit records to an administrator
    """

    return {
        "code": 200,
        "message": "ok",
        "data": get_audit_log_list(
            page=page,
            page_size=page_size,
            operator_id=operator_id,
            action=action,
            target_id=target_id,
            start_time=start_time,
            end_time=end_time,
        ),
    }
