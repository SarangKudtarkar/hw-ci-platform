import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).parent.parent / "db" / "build.db"


def _connect():
    """Create a read-only connection to the CI database."""
    return sqlite3.connect(DB_PATH)


def get_build(build_id: int) -> dict[str, Any] | None:
    """Return information about a single build."""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT
                id,
                commit_hash,
                branch,
                timestamp,
                status,
                runtime_sec
            FROM builds
            WHERE id = ?
            """,
            (build_id,),
        ).fetchone()

    return dict(row) if row else None


def get_stage_results(build_id: int) -> list[dict[str, Any]]:
    """Return all stage results for a build."""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                build_id,
                stage,
                status,
                runtime_sec
            FROM stage_results
            WHERE build_id = ?
            ORDER BY id
            """,
            (build_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_failed_stages(build_id: int) -> list[dict[str, Any]]:
    """Return only failed stages for a build."""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                build_id,
                stage,
                status,
                runtime_sec
            FROM stage_results
            WHERE build_id = ?
              AND status = 'FAIL'
            ORDER BY id
            """,
            (build_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_recent_failures(limit: int = 10) -> list[dict[str, Any]]:
    """Return the most recent failed builds."""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                commit_hash,
                branch,
                timestamp,
                status,
                runtime_sec
            FROM builds
            WHERE status = 'FAIL'
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_timing_results(build_id: int) -> list[dict[str, Any]]:
    """Return timing results for a build."""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                build_id,
                corner,
                setup_wns,
                hold_whs
            FROM timing_results
            WHERE build_id = ?
            ORDER BY corner
            """,
            (build_id,),
        ).fetchall()

    return [dict(row) for row in rows]
