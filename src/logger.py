"""
logger.py
Logs every pipeline run and per-flag user feedback to SQLite, so the log
itself becomes an evaluation/monitoring dataset over time (Day 6 of the plan).
"""
import sqlite3
import os
import json
import hashlib
import datetime
import uuid

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "agent_runs.db")


def _connect(db_path: str = _DEFAULT_DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # timeout=15 makes SQLite wait up to 15s for a lock instead of the 5s
    # default before raising "database is locked" -- WAL mode lets readers
    # and a single writer coexist instead of blocking each other outright.
    # Both matter on hosted platforms (e.g. Streamlit Community Cloud) where
    # reruns can briefly overlap and hit this file concurrently.
    conn = sqlite3.connect(db_path, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            timestamp TEXT,
            input_hash TEXT,
            num_clauses INTEGER,
            num_red_flags INTEGER,
            num_yellow_flags INTEGER,
            report_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            clause_id TEXT,
            useful INTEGER,
            timestamp TEXT
        )
        """
    )
    conn.commit()
    return conn


def log_run(flags: list[dict], db_path: str = _DEFAULT_DB_PATH) -> str:
    """
    Persist a completed run. Returns the run_id.

    Logging is a side-feature (an evaluation/monitoring trail), not the core
    deliverable -- the tenant's report must never fail to render just because
    a local SQLite write hit a lock or a permissions issue on the host. Any
    sqlite3.Error here is caught, and a run_id is still returned so the rest
    of the pipeline (and the UI's feedback buttons) keep working normally;
    that run just won't have a persisted log row.
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    report_json = json.dumps(flags)
    input_hash = hashlib.sha256(report_json.encode("utf-8")).hexdigest()[:16]
    # A random suffix guarantees uniqueness even when the exact same document
    # is re-analyzed within the same second (same input_hash + same second
    # previously collided on the PRIMARY KEY).
    run_id = f"run_{input_hash}_{int(datetime.datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"

    num_red = sum(1 for f in flags if f.get("risk_level") == "red")
    num_yellow = sum(1 for f in flags if f.get("risk_level") == "yellow")

    try:
        conn = _connect(db_path)
        conn.execute(
            "INSERT INTO runs (run_id, timestamp, input_hash, num_clauses, num_red_flags, "
            "num_yellow_flags, report_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, timestamp, input_hash, len(flags), num_red, num_yellow, report_json),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[logger] Warning: could not persist run log ({e}). Continuing without logging.")

    return run_id


def log_feedback(run_id: str, clause_id: str, useful: bool, db_path: str = _DEFAULT_DB_PATH):
    try:
        conn = _connect(db_path)
        conn.execute(
            "INSERT INTO feedback (run_id, clause_id, useful, timestamp) VALUES (?, ?, ?, ?)",
            (run_id, clause_id, int(useful), datetime.datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[logger] Warning: could not persist feedback ({e}).")


def get_all_runs(db_path: str = _DEFAULT_DB_PATH):
    conn = _connect(db_path)
    rows = conn.execute("SELECT run_id, timestamp, num_clauses, num_red_flags, num_yellow_flags FROM runs ORDER BY timestamp DESC").fetchall()
    conn.close()
    return rows
