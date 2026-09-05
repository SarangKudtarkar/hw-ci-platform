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


def create_timing_result(build_id, corner, setup_wns, hold_whs):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO timing_results
            (build_id, corner, setup_wns, hold_whs)
            VALUES (?, ?, ?, ?)
            """,
            (build_id, corner, setup_wns, hold_whs),
        )


def get_timing_results(build_id):
    with connect() as conn:
        return conn.execute(
            """
            SELECT corner, setup_wns, hold_whs
            FROM timing_results
            WHERE build_id = ?
            ORDER BY corner
            """,
            (build_id,),
        ).fetchall()


def get_previous_corner_timing(build_id, corner):
    with connect() as conn:
        return conn.execute(
            """
            SELECT setup_wns, hold_whs
            FROM timing_results
            WHERE build_id < ?
              AND corner = ?
            ORDER BY build_id DESC
            LIMIT 1
            """,
            (build_id, corner),
        ).fetchone()


def get_previous_timing_result(build_id):
    with connect() as conn:
        return conn.execute(
            """
            SELECT setup_wns, hold_whs
            FROM timing_results
            WHERE build_id < ?
            ORDER BY build_id DESC
            LIMIT 1
            """,
            (build_id,),
        ).fetchone()
