import os

from app.repositories.user_repository import (
    create_user,
    find_by_id,
    find_by_username,
)
from app.utils.password import hash_password, verify_password


def _public_user(user: dict) -> dict:
    """
    remove private authentication fields from a user row
    """

    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "is_active": bool(user["is_active"]),
        "last_seen_at": user.get("last_seen_at"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }


def register_user(username: str, password: str) -> dict:
    """
    create a new student account after validation
    """

    normalized_username = username.strip()

    if not 3 <= len(normalized_username) <= 32:
        raise ValueError(
            "username length must be between 3 and 32"
        )

    if len(password) < 8:
        raise ValueError(
            "password must contain at least 8 characters"
        )

    if find_by_username(normalized_username) is not None:
        raise ValueError("username already exists")

    # registration never accepts a role from the client
    user_id = create_user(
        normalized_username,
        hash_password(password),
        role="student",
    )
    user = find_by_id(user_id)

    if user is None:
        raise RuntimeError(
            "created user could not be loaded"
        )

    return _public_user(user)


def authenticate_user(
    username: str,
    password: str,
) -> dict | None:
    """
    verify credentials and return public account data
    """

    user = find_by_username(username.strip())

    if user is None:
        return None

    if not verify_password(
        password,
        user["password_hash"],
    ):
        return None

    if not user["is_active"]:
        raise PermissionError("user is inactive")

    return _public_user(user)


def ensure_initial_admin() -> dict:
    """
    create the initial administrator for a clean database
    """

    username = os.getenv(
        "INITIAL_ADMIN_USERNAME",
        "admin",
    )
    password = os.getenv(
        "INITIAL_ADMIN_PASSWORD",
        "change-me-admin-123",
    )
    existing = find_by_username(username)

    if existing is not None:
        return _public_user(existing)

    user_id = create_user(
        username=username,
        password_hash=hash_password(password),
        role="admin",
    )
    user = find_by_id(user_id)

    if user is None:
        raise RuntimeError(
            "initial administrator could not be loaded"
        )

    return _public_user(user)
