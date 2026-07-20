from app.models.user import UserUpdate
from app.repositories.user_repository import (
    count_users,
    find_public_by_id,
    list_users,
    update_user,
)
from app.services.audit_service import record_audit
from app.utils.time import was_seen_recently


def _prepare_user(user: dict) -> dict:
    """
    convert sqlite values and calculate online presence
    """

    result = dict(user)
    result["is_active"] = bool(result["is_active"])

    # online is calculated from recent activity and is never stored as a flag
    result["is_online"] = (
        result["is_active"]
        and was_seen_recently(
            result.get("last_seen_at"),
            seconds=120,
        )
    )

    return result


def get_user_list(page: int, page_size: int) -> dict:
    """
    return a paginated administrator view of users
    """

    users = [
        _prepare_user(user)
        for user in list_users(
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    ]
    total = count_users()

    return {
        "items": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            total + page_size - 1
        ) // page_size,
    }


def get_user_detail(user_id: int) -> dict:
    """
    return one public user or raise a not found error
    """

    user = find_public_by_id(user_id)

    if user is None:
        raise LookupError("user not found")

    return _prepare_user(user)


def update_user_account(
    user_id: int,
    update_data: UserUpdate,
    current_user: dict,
) -> dict:
    """
    update role and enabled state with audit records
    """

    user = get_user_detail(user_id)

    # prevent an administrator from locking themselves out
    if (
        user_id == current_user["id"]
        and not update_data.is_active
    ):
        raise ValueError(
            "you cannot disable your own account"
        )

    # prevent the current administrator from removing their own role
    if (
        user_id == current_user["id"]
        and update_data.role.value != "admin"
    ):
        raise ValueError(
            "you cannot change your own role"
        )

    role_changed = user["role"] != update_data.role.value
    active_changed = (
        user["is_active"] != update_data.is_active
    )

    if not update_user(
        user_id=user_id,
        role=update_data.role.value,
        is_active=update_data.is_active,
    ):
        raise LookupError("user not found")

    if role_changed:
        record_audit(
            operator_id=current_user["id"],
            action="UPDATE_USER_ROLE",
            target_type="user",
            target_id=user_id,
            detail=(
                f"{user['role']} -> {update_data.role.value}"
            ),
        )

    if active_changed and not update_data.is_active:
        record_audit(
            operator_id=current_user["id"],
            action="DISABLE_USER",
            target_type="user",
            target_id=user_id,
        )

    return get_user_detail(user_id)
