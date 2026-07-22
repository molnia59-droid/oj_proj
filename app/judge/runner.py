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

# keep submitted source files outside the project so uvicorn reload ignores them
TEMP_ROOT = Path(tempfile.gettempdir()) / "mini_online_judge"


def prepare_submission_directory(
    submission_id: int,
    source_code: str,
) -> Path:
    """
    create one isolated directory and save the submitted python file
    """

    # create the shared operating system temp folder when needed
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    # add a random suffix so two submissions can never share files
    submission_directory = TEMP_ROOT / (
        f"submission_{submission_id}_{uuid4().hex}"
    )
    submission_directory.mkdir()

    # save exactly one executable source file for the child process
    code_path = submission_directory / "main.py"
    code_path.write_text(
        source_code,
        encoding="utf-8",
    )

    return submission_directory


def _prepare_stdin(input_data: str) -> bytes:
    """
    pass every entered value as a separate input line
    """

    # split the entered text into separate values
    values = input_data.split()

    # place every value on its own stdin line
    prepared_input = "\n".join(values)

    if prepared_input:
        prepared_input += "\n"

    return prepared_input.encode("utf-8")


def _decode_timeout_output(output_bytes: bytes) -> str:
    """
    decode partial output collected after a timeout
    """

    # timeout logs are diagnostic so undecodable bytes are replaced safely
    return output_bytes.decode(
        "utf-8",
        errors="replace",
    )


def _execute_process(
    submission_directory: Path,
    input_data: str,
    time_limit: float,
) -> dict:
    """
    run student code in a blocking subprocess inside a worker thread
    """

    # use the same python interpreter that runs the fastapi application
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "main.py",
        ],
        cwd=str(submission_directory),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # send the complete multiline testcase through stdin
        stdout_bytes, stderr_bytes = process.communicate(
            input=_prepare_stdin(input_data),
            timeout=time_limit,
        )

        return {
            "timed_out": False,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "exit_code": process.returncode,
        }

    except subprocess.TimeoutExpired:
        # stop infinite loops and collect any output produced before termination
        process.kill()
        stdout_bytes, stderr_bytes = process.communicate()

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
    run one testcase and return a normalized judge result
    """

    start_time = time.perf_counter()

    try:
        # asyncio subprocess support depends on the windows event loop
        # a worker thread with subprocess.Popen works consistently on windows
        execution = await asyncio.to_thread(
            _execute_process,
            submission_directory,
            input_data,
            time_limit,
        )

        time_used = time.perf_counter() - start_time
        stdout_bytes = execution["stdout_bytes"]
        stderr_bytes = execution["stderr_bytes"]
        exit_code = execution["exit_code"]

        if execution["timed_out"]:
            return {
                "result": "TLE",
                "stdout": _decode_timeout_output(
                    stdout_bytes
                ),
                "stderr": _decode_timeout_output(
                    stderr_bytes
                ),
                "exit_code": exit_code,
                "time_used": time_used,
                "memory_used": None,
                "message": "time limit exceeded",
            }

        try:
            # normal output must be valid utf-8 according to the assignment
            stdout = stdout_bytes.decode("utf-8")
            stderr = stderr_bytes.decode("utf-8")
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

        if compare_output(stdout, expected_output):
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
        # unexpected runner failures are system errors and are logged server side
        logger.exception(
            "runner failed inside %s",
            submission_directory,
        )

        return {
            "result": "SE",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "time_used": time.perf_counter() - start_time,
            "memory_used": None,
            "message": f"{type(error).__name__}: {error}",
        }


def cleanup_submission_directory(
    submission_directory: Path,
) -> None:
    """
    remove all temporary files created for one submission
    """

    try:
        if submission_directory.exists():
            shutil.rmtree(submission_directory)
    except Exception:
        # cleanup failure should not replace the real judge result
        logger.exception(
            "failed to remove temporary directory %s",
            submission_directory,
        )
