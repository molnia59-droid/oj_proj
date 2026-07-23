
git ref:https://github.com/molnia59-droid/oj_proj.git

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt


Run
powershell
python -m uvicorn app.main:app --reload --reload-dir app


Open:

text
http://127.0.0.1:8000/


API documentation:

text
http://127.0.0.1:8000/docs


 Initial administrator

A clean database creates:

text
username: admin
password: change-me-admin-123


Values can be changed before the first startup:

powershell
$env:INITIAL_ADMIN_USERNAME="admin"
$env:INITIAL_ADMIN_PASSWORD="admin1234"
$env:SESSION_SECRET="a-long-random-session-secret"
python -m uvicorn app.main:app --reload --reload-dir app


 Tests

powershell
pytest


The current suite contains 15 tests. Tests use temporary databases and do not modify `data/oj.db`.

 Architecture

text
request
  -> router
  -> service
  -> repository
  -> sqlite

submission service
  -> evaluator
  -> runner
  -> python subprocess


text
app/models/          pydantic request validation
app/routers/         async api and html routes
app/services/        business rules and permissions
app/repositories/    parameterized sqlite operations
app/judge/           subprocess execution and comparison
app/utils/           bcrypt time errors and log safety
frontend/templates/  jinja2 html pages
frontend/static/     css and problem form javascript
tests/               pytest coverage
data/oj.db            database created at first startup
data/backups/         administrator backups
report/report.md      project report
UPLOAD_ORDER.txt      numbered submission order


 Roles

- `student` views problems, submits Python and sees only personal restricted logs
- `teacher` manages problems, views all submissions, full logs and rejudge
- `admin` also manages users, audit logs, backup and restore

`is_active` means that an account is enabled. Online presence is calculated from `last_seen_at`. Startup and graceful shutdown clear all presence values. Logout clears the current user presence immediately.

 Passwords

Passwords are stored only as salted bcrypt hashes through `pwdlib[bcrypt]`.

 Judge

Each testcase runs in a separate Python subprocess. The project never uses `eval()` or `exec()`.

text
AC accepted
WA wrong answer
RE runtime error or invalid utf-8
TLE time limit exceeded
SE system error


Failure priority:
SE -> TLE -> RE -> WA


The Windows compatible runner uses `subprocess.Popen` inside `asyncio.to_thread`. Temporary submission files are stored in the operating system temp directory, so Uvicorn reload does not restart when the judge creates `main.py`.

 Logs

Large log fields are limited to 4000 Unicode characters. Hidden testcase input, expected output and stdout are removed from student responses. Absolute server paths are sanitized.

Audit actions include:

text
VIEW_FULL_JUDGE_LOG
REJUDGE_SUBMISSION
UPDATE_USER_ROLE
DISABLE_USER
CREATE_BACKUP
RESTORE_BACKUP


 Backups

text
POST /api/admin/backups
GET  /api/admin/backups
POST /api/admin/backups/{backup_id}/restore


Each backup contains `oj.db` and `manifest.json`. Restore validates the manifest id, required files and SQLite integrity, then keeps a safety copy until replacement succeeds.

 Main API

text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me

GET /api/users
GET /api/users/{user_id}
PUT /api/users/{user_id}

GET    /api/problems
GET    /api/problems/{problem_id}
POST   /api/problems
PUT    /api/problems/{problem_id}
DELETE /api/problems/{problem_id}

POST /api/submissions
GET  /api/submissions
GET  /api/submissions/{submission_id}
POST /api/submissions/{submission_id}/rejudge
GET  /api/submissions/{submission_id}/logs

GET /api/logs
GET /api/audit-logs

POST /api/admin/backups
GET  /api/admin/backups
POST /api/admin/backups/{backup_id}/restore

