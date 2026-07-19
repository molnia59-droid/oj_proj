from datetime import datetime, timedelta, timezone


def utc_now_iso() -> str:
    """
    return the current utc time in iso 8601 format
    """

    # store all project timestamps in one timezone and one text format
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def was_seen_recently(
    value: str | None,
    seconds: int = 120,
) -> bool:
    """
    decide whether a user was active during the recent time window
    """

    # a missing timestamp means the user has not been seen in this session
    if not value:
        return False

    try:
        # convert the stored z suffix into a value accepted by fromisoformat
        seen_at = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        # invalid stored data is treated as offline instead of breaking a page
        return False

    # protect against timestamps that were stored without timezone information
    if seen_at.tzinfo is None:
        seen_at = seen_at.replace(tzinfo=timezone.utc)

    # compare last activity with the configured online window
    threshold = datetime.now(timezone.utc) - timedelta(
        seconds=seconds
    )

    return seen_at >= threshold
