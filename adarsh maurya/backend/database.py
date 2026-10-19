"""
Database configuration and initialization for IRIS one.
Uses Python's built-in sqlite3 module.
"""

import os
import sqlite3
from typing import Optional, Dict, Any, List


def get_db_path() -> str:
    """
    Resolves the SQLite database file location:
    1. DATABASE_PATH or DATABASE_URL environment variables
    2. /data/iris_one.db if persistent volume mount /data exists in container
    3. Local backend/iris_one.db as default fallback
    """
    raw_path = os.environ.get("DATABASE_PATH") or os.environ.get("DATABASE_URL")
    if raw_path:
        if raw_path.startswith("sqlite:///"):
            path = raw_path[len("sqlite:///"):]
        elif raw_path.startswith("sqlite://"):
            path = raw_path[len("sqlite://"):]
        else:
            path = raw_path
        parent_dir = os.path.dirname(os.path.abspath(path))
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception:
                pass
        return path

    if os.path.isdir("/data"):
        return "/data/iris_one.db"

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "iris_one.db")


DB_PATH = get_db_path()


def get_db() -> sqlite3.Connection:
    """
    Returns an SQLite connection with Row factory enabled
    and high-concurrency production PRAGMAs (WAL, NORMAL, busy_timeout=5000).
    """
    target_path = get_db_path()
    parent_dir = os.path.dirname(os.path.abspath(target_path))
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception:
            pass

    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Helper to convert a sqlite3.Row to a standard Python dictionary."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Helper to convert a list of sqlite3.Row objects to dictionaries."""
    return [dict(r) for r in rows]


def find_opportunity(db: sqlite3.Connection, opportunity_id: Any) -> Optional[Dict[str, Any]]:
    """Look up an opportunity by integer id or slug."""
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT * FROM opportunities
        WHERE CAST(id AS TEXT) = ?
           OR LOWER(COALESCE(slug, '')) = LOWER(?)
        """,
        (str(opportunity_id), str(opportunity_id)),
    )
    return row_to_dict(cursor.fetchone())


def _existing_columns(cursor: sqlite3.Cursor, table: str) -> List[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
    if column not in _existing_columns(cursor, table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    """
    Initializes all required database tables for the platform:
    users, opportunities, saved_opportunities, and applications.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            college TEXT DEFAULT '',
            age INTEGER DEFAULT 0,
            state TEXT DEFAULT '',
            country TEXT DEFAULT 'India',
            skills TEXT DEFAULT '',
            domains TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount TEXT DEFAULT '',
            location TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            required_skills TEXT DEFAULT '',
            eligibility_criteria TEXT DEFAULT '',
            url TEXT DEFAULT '',
            is_trending INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE,
            UNIQUE(user_id, opportunity_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            status TEXT DEFAULT 'applied',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE,
            UNIQUE(user_id, opportunity_id)
        )
    """)

    for col, ddl in [
        ("academic_tier", "TEXT DEFAULT ''"),
        ("cgpa_or_percentage", "TEXT DEFAULT ''"),
        ("family_income_lpa", "REAL DEFAULT 8.0"),
        ("extracted_skills", "TEXT DEFAULT ''"),
        ("recommended_domains", "TEXT DEFAULT ''"),
        ("profile_json", "TEXT DEFAULT ''"),
        ("telegram_chat_id", "TEXT DEFAULT ''"),
    ]:
        _ensure_column(cursor, "users", col, ddl)

    for col, ddl in [
        ("slug", "TEXT DEFAULT ''"),
        ("source_portal", "TEXT DEFAULT ''"),
        ("source_url", "TEXT DEFAULT ''"),
        ("category", "TEXT DEFAULT ''"),
        ("financial_value_label", "TEXT DEFAULT ''"),
        ("estimated_value_inr", "INTEGER DEFAULT 0"),
        ("deadline_display", "TEXT DEFAULT ''"),
        ("mode", "TEXT DEFAULT 'PAN India'"),
        ("is_verified_active", "INTEGER DEFAULT 1"),
        ("eligibility_json", "TEXT DEFAULT ''"),
        ("verification_log_json", "TEXT DEFAULT ''"),
    ]:
        _ensure_column(cursor, "opportunities", col, ddl)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
