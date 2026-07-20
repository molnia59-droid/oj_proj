from app.repositories.audit_repository import (
    count_audit_logs,
    create_audit_log,
    list_audit_logs,
)


def record_audit(
    operator_id: int | None,
    action: str,
    target_type: str,
    target_id: str | int | None,
    success: bool = True,
    detail: str | None = None,
) -> None:
    """
    write one audit record through the repository layer
    """

    create_audit_log(
        operator_id=operator_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        success=success,
        detail=detail,
    )


def get_audit_log_list(
    page: int,
    page_size: int,
    operator_id: int | None = None,
    action: str | None = None,
    target_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """
    return paginated audit data with boolean conversion
    """

    items = list_audit_logs(
        limit=page_size,
        offset=(page - 1) * page_size,
        operator_id=operator_id,
        action=action,
        target_id=target_id,
        start_time=start_time,
        end_time=end_time,
    )

    for item in items:
        item["success"] = bool(item["success"])

    total = count_audit_logs(
        operator_id=operator_id,
        action=action,
        target_id=target_id,
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            total + page_size - 1
        ) // page_size,
    }
