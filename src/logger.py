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

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "agent_runs.db")


def _connect(db_path: str = _DEFAULT_DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
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
    """Persist a completed run. Returns the run_id."""
    conn = _connect(db_path)
    timestamp = datetime.datetime.utcnow().isoformat()
    report_json = json.dumps(flags)
    input_hash = hashlib.sha256(report_json.encode("utf-8")).hexdigest()[:16]
    run_id = f"run_{input_hash}_{int(datetime.datetime.utcnow().timestamp())}"

    num_red = sum(1 for f in flags if f.get("risk_level") == "red")
    num_yellow = sum(1 for f in flags if f.get("risk_level") == "yellow")

    conn.execute(
        "INSERT INTO runs (run_id, timestamp, input_hash, num_clauses, num_red_flags, "
        "num_yellow_flags, report_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_id, timestamp, input_hash, len(flags), num_red, num_yellow, report_json),
    )
    conn.commit()
    conn.close()
    return run_id


def log_feedback(run_id: str, clause_id: str, useful: bool, db_path: str = _DEFAULT_DB_PATH):
    conn = _connect(db_path)
    conn.execute(
        "INSERT INTO feedback (run_id, clause_id, useful, timestamp) VALUES (?, ?, ?, ?)",
        (run_id, clause_id, int(useful), datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_runs(db_path: str = _DEFAULT_DB_PATH):
    conn = _connect(db_path)
    rows = conn.execute("SELECT run_id, timestamp, num_clauses, num_red_flags, num_yellow_flags FROM runs ORDER BY timestamp DESC").fetchall()
    conn.close()
    return rows
