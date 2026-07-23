FINAL PYTEST SUITE

Contents

tests/conftest.py
Shared fixture and helper functions

tests/test_auth.py
Registration login roles and account blocking

tests/test_presence.py
Logout last_seen_at online and offline

tests/test_problems.py
Problem creation validation editing and student permissions

tests/test_submissions.py
AC WA RE and partial scoring

tests/test_judge.py
Multiline stdin per testcase time limit TLE and output comparison

tests/test_security.py
Hidden testcase logs output truncation and path sanitization

tests/test_backup.py
Backup creation listing restore corruption and manifest checks

tests/test_web.py
Main HTML pages and multiline textarea fields


INSTALLATION

1. Stop the FastAPI server

2. Delete the old tests folder

PowerShell:

Remove-Item -Recurse -Force tests

3. Extract this archive into the project root

The result must look like:

project_root/
    app/
    frontend/
    tests/
        __init__.py
        conftest.py
        test_auth.py
        test_presence.py
        test_problems.py
        test_submissions.py
        test_judge.py
        test_security.py
        test_backup.py
        test_web.py

4. Activate the virtual environment

PowerShell:

.\\.venv\\Scripts\\Activate.ps1

5. Install pytest when needed

python -m pip install pytest

6. Run all tests

pytest -v

7. Run one file

pytest tests/test_judge.py -v

8. Run one test function

pytest tests/test_judge.py::test_each_testcase_receives_full_time_limit -v


IMPORTANT

The tests use a temporary SQLite database

The real data/oj.db file should not be modified

The tests expect the final project behavior

- logout preserves last_seen_at
- online status is calculated from recent last_seen_at
- every testcase receives its own full time limit
- multiline stdin is preserved
- hidden tests are protected
- backup restore validates database integrity
