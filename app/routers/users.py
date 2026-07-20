from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_roles
from app.models.user import UserUpdate
from app.services.user_service import (
    get_user_detail,
    get_user_list,
    update_user_account,
)


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def get_users_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _current_user: dict = Depends(require_roles("admin")),
):
    """
    return the paginated user list to an administrator
    """

    return {
        "code": 200,
        "message": "ok",
        "data": get_user_list(page, page_size),
    }


@router.get("/{user_id}")
async def get_user_endpoint(
    user_id: int,
    _current_user: dict = Depends(require_roles("admin")),
):
    """
    return one user to an administrator
    """

    try:
        user = get_user_detail(user_id)
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
        "message": "ok",
        "data": user,
    }


@router.put("/{user_id}")
async def update_user_endpoint(
    user_id: int,
    update_data: UserUpdate,
    current_user: dict = Depends(require_roles("admin")),
):
    """
    update role and account state in one exact endpoint
    """

    try:
        user = update_user_account(
            user_id,
            update_data,
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
    except ValueError as error:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": str(error),
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "user updated",
        "data": user,
    }
