# database.py
# ============================================================
# SQLite database helpers for HR Provisioning Portal
#
# - init_db()       : creates base tables (safe to run many times)
# - ensure_schema() : safe migrations (adds missing columns/tables)
#
# NOTE (best practice):
# - Workflow audit (per request) goes into "audit"
# - Auth/session events go into "security_audit"
# ============================================================

import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("hr_portal.db")


# ------------------------------------------------------------
# Connection
# ------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# Time helper
# ------------------------------------------------------------
def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ------------------------------------------------------------
# Base DB init (tables)
# ------------------------------------------------------------
def init_db() -> None:
    """
    Creates core tables if missing.
    Safe to run on every app startup.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Main requests table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,                 -- 'onboard' or 'offboard'
            status TEXT NOT NULL,               -- 'submitted','approved','rejected','it_pending','executed','failed'
            payload_json TEXT NOT NULL,         -- request body stored as JSON text
            created_by TEXT NOT NULL,           -- UPN
            created_at TEXT NOT NULL,
            approved_by TEXT,
            approved_at TEXT,
            rejected_by TEXT,
            rejected_at TEXT,
            rejected_reason TEXT,
            decided_by TEXT,
            decided_at TEXT,
            executed_at TEXT,
            result_json TEXT
        )
        """
    )

    # Request audit trail
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            actor TEXT NOT NULL,               -- display name or 'system'
            action TEXT NOT NULL,              -- 'submit','approve','reject','execute','fail', etc.
            details TEXT,
            at TEXT NOT NULL
        )
        """
    )

    # Employee number generator (single row)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_sequence (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_number INTEGER NOT NULL
        )
        """
    )
    cur.execute("INSERT OR IGNORE INTO employee_sequence (id, last_number) VALUES (1, 1000)")

    # Employee registry (optional mapping)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            employee_number INTEGER PRIMARY KEY,
            upn TEXT,
            object_id TEXT,
            status TEXT NOT NULL,          -- 'requested','active','disabled'
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        """
    )

    # Security audit (auth/session)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS security_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL,
            user_upn TEXT,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            meta_json TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# ------------------------------------------------------------
# Audit helpers
# ------------------------------------------------------------
def audit_log(request_id: int | None, actor: str, action: str, details: str = "") -> None:
    """
    Workflow audit (tied to a request_id).
    """
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO audit(request_id, actor, action, details, at) VALUES (?,?,?,?,?)",
            (request_id, actor, action, details, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def security_audit_log(user_upn: str | None, action: str, details: str, meta: dict | None = None) -> None:
    """
    Security audit (NOT tied to a request).

    WHY:
    - Sign-in/session issues are security events, not HR workflow events
    """
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO security_audit(at, user_upn, action, details, meta_json) VALUES (?,?,?,?,?)",
            (now_iso(), (user_upn or ""), action, details, json.dumps(meta or {})),
        )
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------
# Schema migration helpers (SQLite safe migrations)
# ------------------------------------------------------------
def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


def ensure_schema() -> None:
    """
    Safe schema migration for SQLite (educational repo).
    Adds missing columns/tables if they don't exist.
    """
    conn = get_conn()
    cur = conn.cursor()

    # --- Add missing columns in requests table (if your DB was created earlier) ---
    if not _column_exists(conn, "requests", "rejected_by"):
        cur.execute("ALTER TABLE requests ADD COLUMN rejected_by TEXT")

    if not _column_exists(conn, "requests", "rejected_at"):
        cur.execute("ALTER TABLE requests ADD COLUMN rejected_at TEXT")

    if not _column_exists(conn, "requests", "rejected_reason"):
        cur.execute("ALTER TABLE requests ADD COLUMN rejected_reason TEXT")

    if not _column_exists(conn, "requests", "decided_by"):
        cur.execute("ALTER TABLE requests ADD COLUMN decided_by TEXT")

    if not _column_exists(conn, "requests", "decided_at"):
        cur.execute("ALTER TABLE requests ADD COLUMN decided_at TEXT")

    # --- Ensure employee_sequence exists ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_sequence (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_number INTEGER NOT NULL
        )
        """
    )
    cur.execute("INSERT OR IGNORE INTO employee_sequence (id, last_number) VALUES (1, 1000)")

    # --- Ensure employees exists ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            employee_number INTEGER PRIMARY KEY,
            upn TEXT,
            object_id TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        """
    )

    # --- Ensure security_audit exists ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS security_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL,
            user_upn TEXT,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            meta_json TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# ------------------------------------------------------------
# Employee number generator
# ------------------------------------------------------------
def next_employee_number() -> int:
    """
    Generate next employee number safely.
    Uses a DB transaction to avoid duplicates.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Lock for write to avoid duplicates (important even in small apps)
    cur.execute("BEGIN IMMEDIATE")

    row = cur.execute("SELECT last_number FROM employee_sequence WHERE id = 1").fetchone()
    if not row:
        cur.execute("INSERT OR IGNORE INTO employee_sequence (id, last_number) VALUES (1, 1000)")
        last_number = 1000
    else:
        last_number = int(row["last_number"])

    next_num = last_number + 1
    cur.execute("UPDATE employee_sequence SET last_number = ? WHERE id = 1", (next_num,))

    conn.commit()
    conn.close()
    return next_num
