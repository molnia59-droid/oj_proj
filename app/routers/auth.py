from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.dependencies.auth import get_current_user
from app.models.auth import LoginRequest, RegisterRequest
from app.repositories.user_repository import (
    clear_user_presence,
    touch_user_last_seen,
)
from app.services.auth_service import (
    authenticate_user,
    register_user,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(request_data: RegisterRequest):
    """
    create a student account with the standard api response format
    """

    try:
        user = register_user(
            request_data.username,
            request_data.password,
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

    return {
        "code": 201,
        "message": "user created",
        "data": user,
    }


@router.post("/login")
async def login(
    request: Request,
    request_data: LoginRequest,
):
    """
    verify credentials and store the user id in the session
    """

    try:
        user = authenticate_user(
            request_data.username,
            request_data.password,
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

    if user is None:
        return JSONResponse(
            status_code=401,
            content={
                "code": 401,
                "message": "invalid username or password",
                "data": None,
            },
        )

    # discard any stale session data before creating the new login
    request.session.clear()
    request.session["user_id"] = user["id"]
    touch_user_last_seen(user["id"])

    return {
        "code": 200,
        "message": "login successful",
        "data": user,
    }


@router.get("/me")
async def get_current_user_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """
    return the currently authenticated public user
    """

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "id": current_user["id"],
            "username": current_user["username"],
            "role": current_user["role"],
            "is_active": bool(current_user["is_active"]),
            "last_seen_at": current_user.get("last_seen_at"),
            "created_at": current_user["created_at"],
            "updated_at": current_user["updated_at"],
        },
    }


@router.post("/logout")
async def logout(request: Request):
    """
    clear the current session cookie data
    """

    user_id = request.session.get("user_id")

    if user_id is not None:
        clear_user_presence(user_id)

    request.session.clear()

    return {
        "code": 200,
        "message": "logout successful",
        "data": None,
    }
