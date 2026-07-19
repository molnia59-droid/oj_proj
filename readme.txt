
This part uses:
- database.py
- models
- utilities
- comparator.py



1. app/repositories/user_repository.py

Handles database operations for the users table

Main functions:
- find_by_username
- create_user
- find_by_id
- find_public_by_id
- list_users
- count_users
- update_user
- touch_user_last_seen
- clear_user_presence
- clear_all_user_presence

Logic:
- password_hash is returned only when it is actually required
- public methods do not return password_hash
- last_seen_at is updated when the user is active
- online status is calculated instead of stored permanently
- logout can clear last_seen_at immediately


2. app/repositories/problem_repository.py

Handles problems and test_cases

Main functions:
- create_problem
- find_problem_by_id
- list_problems
- count_problems
- find_problem_with_tests
- update_problem
- soft_delete_problem

Logic:
- samples and tags are stored as JSON
- test cases are stored in a separate table
- deletion uses the is_deleted field
- old submissions keep their relationship with the problem


3. app/repositories/submission_repository.py

Handles submissions and test_logs

Main functions:
- create_submission
- find_submission_by_id
- mark_submission_running
- finish_submission
- mark_submission_failed
- list_submissions
- count_submissions
- reset_submission_for_rejudge
- list_submission_test_logs
- list_test_logs
- count_test_logs
- fail_submission_with_logs

Logic:
- status transitions between pending, running, finished, and failed are controlled
- results and logs are saved transactionally
- judge output is truncated before being written
- submission and log filters are supported


4. app/repositories/audit_repository.py

Handles audit_logs

Main functions:
- create_audit_log
- list_audit_logs
- count_audit_logs

Stored fields:
- operator_id
- action
- target_type
- target_id
- success
- detail
- created_at


5. app/repositories/backup_repository.py

Handles the backups table

Main functions:
- create_backup_record
- list_backup_records
- find_backup_record

The table stores backup metadata
The actual database file is copied by backup_service in Part 3


6. app/judge/runner.py

Runs student code

Main functions:
- prepare_submission_directory
- _execute_process
- run_test_case
- cleanup_submission_directory

Logic:
- code is saved as main.py
- code runs in a separate subprocess
- subprocess.Popen is used
- the blocking subprocess runs through asyncio.to_thread
- this works with Uvicorn on Windows
- input is passed through stdin
- stdout and stderr are captured separately
- timeout terminates the process
- invalid UTF-8 produces RE
- temporary files are created outside the project directory
- Uvicorn reload does not react to generated student main.py files


7. app/judge/evaluator.py

Evaluates a solution against all test cases

Main functions:
- choose_overall_result
- judge_solution

Logic:
- every test case runs separately
- score is awarded only for AC
- the final result uses this priority:
  SE
  TLE
  RE
  WA
- individual test logs are returned
- the temporary directory is removed in finally

