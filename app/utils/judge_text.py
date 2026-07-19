import re
from pathlib import Path


MAX_LOG_TEXT_LENGTH = 4000
TRUNCATION_MARKER = "...[truncated]"

WINDOWS_PATH_PATTERN = re.compile(
    r'(?i)(?<![\w])[a-z]:[\\/][^"\r\n]+'
)

UNIX_PATH_PATTERN = re.compile(
    r'(?<![\w])/(?:[^/\s"\r\n]+/)+[^/\s"\r\n]+'
)


def truncate_text(
    text: str | None,
    limit: int = MAX_LOG_TEXT_LENGTH,
) -> str:
    """
    limit stored log text
    """

    if text is None:
        return ""

    if len(text) <= limit:
        return text

    return text[:limit] + TRUNCATION_MARKER


def sanitize_error_message(
    text: str | None,
    submission_directory: Path | None = None,
) -> str:
    """
    remove absolute server paths from an error message
    """

    if text is None:
        return ""

    sanitized = text

    if submission_directory is not None:
        directory_text = str(
            submission_directory.resolve()
        )

        sanitized = sanitized.replace(
            directory_text,
            "<submission>",
        )

        sanitized = sanitized.replace(
            directory_text.replace("\\", "/"),
            "<submission>",
        )

    sanitized = WINDOWS_PATH_PATTERN.sub(
        _replace_absolute_path,
        sanitized,
    )

    sanitized = UNIX_PATH_PATTERN.sub(
        _replace_absolute_path,
        sanitized,
    )

    return sanitized


def _replace_absolute_path(
    match: re.Match,
) -> str:
    """
    convert an absolute path into a safe value
    """

    path_text = match.group(0)

    normalized = path_text.replace(
        "\\",
        "/",
    ).lower()

    if normalized.endswith("/main.py"):
        return "<submission>/main.py"

    return "<path>"