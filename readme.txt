
all comments are in the code

 requirements.txt

Main dependencies:
- FastAPI
- Uvicorn
- Jinja2
- python-multipart
- bcrypt
- itsdangerous
- pytest
- httpx

 app/models

Pydantic models for validating input data were added

app/models/auth.py
- RegisterRequest
- LoginRequest
- username length validation
- minimum password length validation

app/models/user.py
- UserRole
- UserUpdate
- allowed roles: student, teacher, and admin

app/models/problem.py
- Difficulty
- SampleData
- TestCaseCreate
- ProblemBase
- ProblemCreate
- ProblemUpdate
- validation that at least one test exists
- validation that case_id values are unique
- validation that the total test score equals 100

app/models/submission.py
- SubmissionCreate
- validation that the language is Python
- validation that source_code is not empty
- source code size limit of 64 KiB


app/utils

app/utils/exception_handlers.py
- unified API error format
- HTTPException handling
- Pydantic validation error handling
- unexpected exception handling

app/utils/judge_text.py
- truncate_text
- limits judge logs to 4000 characters
- sanitize_error_message
- removes absolute server paths from errors

app/utils/password.py
- hash_password
- verify_password
- bcrypt password hashing

app/utils/time.py
- utc_now_iso
- creates UTC timestamps in ISO 8601 format
- was_seen_recently
- calculates online status from last_seen_at


 app/repositories/database.py

A clean SQLite schema was created without legacy database migration

Functions:
- get_connection
- init_db

Created tables:
- users
- problems
- test_cases
- submissions
- test_logs
- audit_logs
- backups

Important details:
- foreign keys are enabled
- problem IDs are stored as strings
- last_seen_at is separate from is_active
- created_at and other timestamps are stored in UTC
- old databases are not migrated automatically


 app/judge/comparator.py

Functions:
- normalize_output
- compare_output

Comparison rules:
- CRLF is converted to LF
- trailing spaces are ignored
- extra empty lines at the end are ignored
- leading and internal spaces are preserved

 Support files

Added:
- app/__init__.py
- __init__.py files for Python packages
- data/backups/.gitkeep
- temp/.gitkeep


