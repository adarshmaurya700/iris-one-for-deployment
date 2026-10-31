"""
Database configuration and initialization for IRIS one.
Uses Python's built-in sqlite3 module.
"""

import os
import sqlite3
import json
import logging
import re
from typing import Optional, Dict, Any, List


def get_db_path() -> str:
    """
    Resolves the SQLite database file location:
    1. DATABASE_PATH or DATABASE_URL environment variables
    2. /data/iris_one.db if persistent volume mount /data exists in container
    3. Local backend/iris_one.db as default fallback
    """
    raw_path = os.environ.get("DATABASE_PATH")
    database_url = os.environ.get("DATABASE_URL", "")
    if not raw_path and not database_url.startswith(("postgres://", "postgresql://")):
        raw_path = database_url
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


_postgres_available = None


class DatabaseRow(dict):
    """Keep the existing sqlite Row interface on PostgreSQL."""
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class PostgresCursor:
    def __init__(self, connection):
        self.connection = connection
        self.raw = connection.raw.cursor()
        self.lastrowid = None

    @property
    def rowcount(self):
        return self.raw.rowcount

    def execute(self, sql, params=()):
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        if 'INSERT OR IGNORE INTO' in sql.upper():
            sql = re.sub('INSERT OR IGNORE INTO', 'INSERT INTO', sql, flags=re.I).rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
        sql = sql.replace("?", "%s")
        inserted = bool(re.match(r"\s*INSERT\s+INTO\s+(users|opportunities|applications|saved_opportunities|tracked_applications|sync_runs)\b", sql, re.I))
        if inserted and "RETURNING" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        self.raw.execute(sql, params)
        if inserted:
            row = self.raw.fetchone()
            self.lastrowid = row["id"] if row else None
        return self

    def fetchone(self):
        row = self.raw.fetchone()
        return DatabaseRow(row) if row is not None else None

    def fetchall(self):
        return [DatabaseRow(row) for row in self.raw.fetchall()]


class PostgresConnection:
    def __init__(self, raw):
        self.raw = raw

    def cursor(self):
        return PostgresCursor(self)

    def execute(self, sql, params=()):
        return self.cursor().execute(sql, params)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def get_db() -> sqlite3.Connection:
    """
    Returns an SQLite connection with Row factory enabled
    and high-concurrency production PRAGMAs (WAL, NORMAL, busy_timeout=5000).
    """
    global _postgres_available
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url.startswith(("postgres://", "postgresql://")) and (_postgres_available is not False or __import__('runtime_config').production()):
        try:
            import psycopg
            from psycopg.rows import dict_row
            conn = PostgresConnection(psycopg.connect(database_url, row_factory=dict_row, connect_timeout=3))
            _postgres_available = True
            return conn
        except Exception:
            from runtime_config import production
            if _postgres_available or production():
                raise  # Never split an established database across two stores.
            logging.getLogger(__name__).warning("PostgreSQL unavailable at startup; using local SQLite.")
            _postgres_available = False
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


def db_session():
    connection = get_db()
    try:
        yield connection
    finally:
        connection.close()


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
    if isinstance(cursor, PostgresCursor):
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = ?", (table,))
        return [row[0] for row in cursor.fetchall()]
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
        ("family_income_lpa", "REAL"),
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

    for column, ddl in OPPORTUNITY_COLUMNS.items():
        _ensure_column(cursor, "opportunities", column, ddl)
    cursor.execute("""CREATE TABLE IF NOT EXISTS student_profiles (
        id TEXT PRIMARY KEY, name TEXT DEFAULT '', email TEXT DEFAULT '',
        academic_stage TEXT DEFAULT '', institution TEXT DEFAULT '',
        academic_tier TEXT DEFAULT '', state_domicile TEXT DEFAULT '',
        age INTEGER, class_12_pct REAL, family_income_inr INTEGER, nirf_top_50 INTEGER,
        skills_json TEXT DEFAULT '[]', resume_text TEXT DEFAULT '',
        profile_completeness INTEGER DEFAULT 0, embedding_json TEXT DEFAULT '[]'
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS tracked_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
        opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'In Progress', checked_documents_json TEXT DEFAULT '[]',
        updated_at TEXT NOT NULL, UNIQUE(student_id, opportunity_id)
    )""")
    for column, ddl in {
        'country': "TEXT DEFAULT 'India'", 'graduation_year': 'INTEGER',
        'domains_json': "TEXT DEFAULT '[]'", 'areas_of_interest': "TEXT DEFAULT ''",
        'resume_filename': "TEXT DEFAULT ''", 'resume_uploaded_at': "TEXT DEFAULT ''",
        'onboarding_complete': 'INTEGER DEFAULT 0', 'preferences_json': "TEXT DEFAULT '{}'",
    }.items():
        _ensure_column(cursor, 'student_profiles', column, ddl)
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile_saved (
        student_id TEXT NOT NULL, opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL, PRIMARY KEY(student_id, opportunity_id)
    )''')
    cursor.execute("""CREATE TABLE IF NOT EXISTS sync_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_type TEXT NOT NULL,
        opportunities_updated INTEGER NOT NULL DEFAULT 0, fake_links_purged INTEGER DEFAULT 0,
        status TEXT NOT NULL, executed_at TEXT NOT NULL, completed_at TEXT,
        summary_json TEXT DEFAULT '{}'
    )""")
    cursor.execute("CREATE TABLE IF NOT EXISTS worker_locks (name TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at TEXT NOT NULL)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalog_status ON opportunities(is_verified_active, category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalog_slug ON opportunities(slug)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_student ON tracked_applications(student_id, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_executed ON sync_runs(executed_at)")
    conn.commit()
    if isinstance(conn, PostgresConnection):
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute("ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS embedding vector(128)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_vector ON opportunities USING hnsw (embedding vector_cosine_ops)")
            conn.commit()
        except Exception:
            conn.rollback()
            logging.getLogger(__name__).warning("pgvector unavailable; using portable embedding_json retrieval.")
    conn.close()


OPPORTUNITY_COLUMNS = {
    "provider": "TEXT DEFAULT ''", "academic_tier": "TEXT DEFAULT 'ALL'",
    "benefit_summary": "TEXT DEFAULT ''", "amount_inr": "INTEGER DEFAULT 0",
    "deadline_iso": "TEXT DEFAULT ''", "location_state": "TEXT DEFAULT 'All India'",
    "min_marks_pct": "REAL DEFAULT 0", "max_family_income_inr": "INTEGER DEFAULT 99999999",
    "nirf_top_50_required": "INTEGER DEFAULT 0", "is_exclusive_tuition_grant": "INTEGER DEFAULT 0",
    "is_sponsored": "INTEGER DEFAULT 0", "apply_url": "TEXT DEFAULT ''",
    "secondary_url": "TEXT DEFAULT ''", "rules_pdf_url": "TEXT DEFAULT ''",
    "how_to_apply_steps_json": "TEXT DEFAULT '[]'", "required_documents_json": "TEXT DEFAULT '[]'",
    "application_channels_json": "TEXT DEFAULT '[]'", "skills_tags_json": "TEXT DEFAULT '[]'",
    "embedding_json": "TEXT DEFAULT '[]'", "verification_status": "TEXT DEFAULT 'SEEDED_CACHE'",
    "last_verified_at": "TEXT DEFAULT ''", "last_checked_at": "TEXT DEFAULT ''",
}


def update_embedding(db, opportunity_id, vector):
    db.execute("UPDATE opportunities SET embedding_json = ? WHERE id = ?", (json.dumps(vector), opportunity_id))
    if isinstance(db, PostgresConnection):
        # A savepoint preserves the rest of the transaction if pgvector is absent.
        db.execute("SAVEPOINT vector_update")
        try:
            db.execute("UPDATE opportunities SET embedding = ?::vector WHERE id = ?", (json.dumps(vector), opportunity_id))
        except Exception:
            db.execute("ROLLBACK TO SAVEPOINT vector_update")
        finally:
            db.execute("RELEASE SAVEPOINT vector_update")


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
