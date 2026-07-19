from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

from app.repositories.user_repository import (
    find_by_id,
    touch_user_last_seen,
)


async def get_current_user(request: Request) -> dict:
    """
    return the authenticated active user for an api request
    """

    # read only the user id from the signed session cookie
    user_id = request.session.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="not authenticated",
        )

    # load fresh role and active state data on every request
    user = find_by_id(user_id)

    if user is None:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="invalid session",
        )

    if not user["is_active"]:
        request.session.clear()
        raise HTTPException(
            status_code=403,
            detail="user is inactive",
        )

    # update presence only after authentication succeeds
    touch_user_last_seen(user["id"])
    user["is_active"] = bool(user["is_active"])

    return user


def require_roles(*allowed_roles: str) -> Callable:
    """
    build a reusable dependency that checks backend roles
    """

    async def role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        """
        check the current user role against the allowed role set
        """

        # frontend visibility is not trusted so permission is checked here
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="permission denied",
            )

        return current_user

    return role_checker
