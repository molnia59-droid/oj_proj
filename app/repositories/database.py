import sqlite3
from pathlib import Path


# resolve every persistent path from the project root
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "oj.db"
BACKUP_DIR = DATA_DIR / "backups"


def get_connection() -> sqlite3.Connection:
    """
    open one configured sqlite connection
    """

    # create the data directory before sqlite opens the database file
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # use a timeout so short concurrent writes can wait instead of failing
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
    )

    # return rows that can be converted directly into dictionaries
    connection.row_factory = sqlite3.Row

    # enforce relationships declared with foreign keys
    connection.execute("PRAGMA foreign_keys = ON")

    # allow readers while another connection writes to the database
    connection.execute("PRAGMA journal_mode = WAL")

    return connection


def init_db() -> None:
    """
    create the clean database schema when it does not exist
    """

    # create folders used by the database and backup features
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    connection = get_connection()

    try:
        # create every table required by the project
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student'
                    CHECK (role IN ('student', 'teacher', 'admin')),
                is_active INTEGER NOT NULL DEFAULT 1,
                last_seen_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS problems (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                input_description TEXT NOT NULL,
                output_description TEXT NOT NULL,
                samples TEXT NOT NULL,
                constraints_text TEXT NOT NULL DEFAULT '',
                time_limit REAL NOT NULL CHECK (time_limit > 0),
                memory_limit INTEGER NOT NULL CHECK (memory_limit > 0),
                difficulty TEXT NOT NULL
                    CHECK (difficulty IN ('easy', 'medium', 'hard')),
                tags TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                input_data TEXT NOT NULL,
                expected_output TEXT NOT NULL,
                score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
                is_hidden INTEGER NOT NULL DEFAULT 1,
                UNIQUE (problem_id, case_id),
                FOREIGN KEY (problem_id)
                    REFERENCES problems(id)
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                problem_id TEXT NOT NULL,
                language TEXT NOT NULL
                    CHECK (language = 'python'),
                source_code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN (
                            'pending',
                            'running',
                            'finished',
                            'failed'
                        )
                    ),
                result TEXT
                    CHECK (
                        result IS NULL
                        OR result IN ('AC', 'WA', 'RE', 'TLE', 'SE')
                    ),
                score INTEGER NOT NULL DEFAULT 0
                    CHECK (score BETWEEN 0 AND 100),
                total_time REAL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY (user_id)
                    REFERENCES users(id),
                FOREIGN KEY (problem_id)
                    REFERENCES problems(id)
            );

            CREATE TABLE IF NOT EXISTS test_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                case_id TEXT NOT NULL,
                result TEXT NOT NULL
                    CHECK (result IN ('AC', 'WA', 'RE', 'TLE', 'SE')),
                score INTEGER NOT NULL,
                maximum_score INTEGER NOT NULL,
                time_used REAL NOT NULL,
                memory_used INTEGER,
                exit_code INTEGER,
                input_data TEXT NOT NULL,
                expected_output TEXT NOT NULL,
                stdout TEXT NOT NULL,
                stderr TEXT NOT NULL,
                message TEXT NOT NULL,
                is_hidden INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (submission_id)
                    REFERENCES submissions(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id INTEGER,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT,
                success INTEGER NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (operator_id)
                    REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS backups (
                backup_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                storage_type TEXT NOT NULL,
                file_list TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY (created_by)
                    REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_submissions_user
                ON submissions(user_id);

            CREATE INDEX IF NOT EXISTS idx_submissions_problem
                ON submissions(problem_id);

            CREATE INDEX IF NOT EXISTS idx_submissions_created
                ON submissions(created_at);

            CREATE INDEX IF NOT EXISTS idx_test_logs_submission
                ON test_logs(submission_id);

            CREATE INDEX IF NOT EXISTS idx_audit_action
                ON audit_logs(action);

            CREATE INDEX IF NOT EXISTS idx_audit_created
                ON audit_logs(created_at);
            """
        )

        # save schema creation as one transaction
        connection.commit()

    finally:
        # always release the database file handle
        connection.close()
