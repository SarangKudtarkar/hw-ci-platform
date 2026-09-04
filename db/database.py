import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent / "build.db"


def connect():
    return sqlite3.connect(DB_PATH)


def create_build(commit_hash, branch, timestamp, status, runtime_sec):
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO builds
            (commit_hash, branch, timestamp, status, runtime_sec)
            VALUES (?, ?, ?, ?, ?)
            """,
            (commit_hash, branch, timestamp, status, runtime_sec),
        )
        return cursor.lastrowid


def create_stage_result(build_id, stage, status, runtime_sec):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO stage_results
            (build_id, stage, status, runtime_sec)
            VALUES (?, ?, ?, ?)
            """,
            (build_id, stage, status, runtime_sec),
        )
