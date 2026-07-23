import asyncio
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.judge.comparator import compare_output


logger = logging.getLogger(__name__)

# keep submitted source files outside the project folder
TEMP_ROOT = Path(tempfile.gettempdir()) / "mini_online_judge"


def prepare_submission_directory(
    submission_id: int,
    source_code: str,
) -> Path:
    """
    create one temporary submission directory
    """

    TEMP_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    submission_directory = TEMP_ROOT / (
        f"submission_{submission_id}_{uuid4().hex}"
    )

    submission_directory.mkdir()

    source_file = (
        submission_directory
        / "main.py"
    )

    source_file.write_text(
        source_code,
        encoding="utf-8",
    )

    return submission_directory


def _prepare_stdin(
    input_data: str,
) -> bytes:
    """
    preserve the original input line structure
    """

    # normalize windows and old mac line endings
    prepared_input = input_data.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    # add one final newline without changing existing lines
    if (
        prepared_input
        and not prepared_input.endswith("\n")
    ):
        prepared_input += "\n"

    return prepared_input.encode(
        "utf-8"
    )


def _decode_output(
    output_data: bytes,
) -> str:
    """
    decode diagnostic output safely
    """

    return output_data.decode(
        "utf-8",
        errors="replace",
    )


def _execute_process(
    submission_directory: Path,
    input_data: str,
    time_limit: float,
) -> dict:
    """
    execute submitted code in a blocking subprocess
    """

    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "main.py",
        ],
        cwd=str(
            submission_directory
        ),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = (
            process.communicate(
                input=_prepare_stdin(
                    input_data
                ),
                timeout=time_limit,
            )
        )

        return {
            "timed_out": False,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "exit_code": process.returncode,
        }

    except subprocess.TimeoutExpired:
        process.kill()

        stdout_bytes, stderr_bytes = (
            process.communicate()
        )

        return {
            "timed_out": True,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "exit_code": process.returncode,
        }


async def run_test_case(
    submission_directory: Path,
    input_data: str,
    expected_output: str,
    time_limit: float,
) -> dict:
    """
    run one testcase with its own time limit
    """

    start_time = time.perf_counter()

    try:
        execution = await asyncio.to_thread(
            _execute_process,
            submission_directory,
            input_data,
            time_limit,
        )

        time_used = (
            time.perf_counter()
            - start_time
        )

        stdout_bytes = execution[
            "stdout_bytes"
        ]

        stderr_bytes = execution[
            "stderr_bytes"
        ]

        exit_code = execution[
            "exit_code"
        ]

        if execution["timed_out"]:
            return {
                "result": "TLE",
                "stdout": _decode_output(
                    stdout_bytes
                ),
                "stderr": _decode_output(
                    stderr_bytes
                ),
                "exit_code": exit_code,
                "time_used": time_used,
                "memory_used": None,
                "message": (
                    "time limit exceeded"
                ),
            }

        try:
            stdout = stdout_bytes.decode(
                "utf-8"
            )

            stderr = stderr_bytes.decode(
                "utf-8"
            )

        except UnicodeDecodeError:
            return {
                "result": "RE",
                "stdout": "",
                "stderr": "",
                "exit_code": exit_code,
                "time_used": time_used,
                "memory_used": None,
                "message": (
                    "program output is not valid utf-8"
                ),
            }

        if exit_code != 0:
            return {
                "result": "RE",
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "time_used": time_used,
                "memory_used": None,
                "message": "runtime error",
            }

        if compare_output(
            stdout,
            expected_output,
        ):
            return {
                "result": "AC",
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "time_used": time_used,
                "memory_used": None,
                "message": "accepted",
            }

        return {
            "result": "WA",
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "time_used": time_used,
            "memory_used": None,
            "message": (
                "output does not match expected answer"
            ),
        }

    except Exception as error:
        logger.exception(
            "runner failed inside %s",
            submission_directory,
        )

        return {
            "result": "SE",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "time_used": (
                time.perf_counter()
                - start_time
            ),
            "memory_used": None,
            "message": (
                f"{type(error).__name__}: {error}"
            ),
        }


def cleanup_submission_directory(
    submission_directory: Path,
) -> None:
    """
    remove temporary submission files
    """

    try:
        if submission_directory.exists():
            shutil.rmtree(
                submission_directory
            )

    except Exception:
        logger.exception(
            "failed to remove temporary directory %s",
            submission_directory,
        )
