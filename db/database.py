import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent / "build.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Builds recorded before the design column existed were all run on this IP.
LEGACY_DESIGN = "async_fifo"

_prepared = set()


def _add_column_if_missing(conn, table, column, definition):
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column in existing:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return True


def ensure_schema(conn):
    """Create missing tables and upgrade databases made by older versions."""
    conn.executescript(SCHEMA_PATH.read_text())

    _add_column_if_missing(conn, "timing_results", "corner", "TEXT")

    if _add_column_if_missing(conn, "builds", "design", "TEXT"):
        conn.execute(
            "UPDATE builds SET design = ? WHERE design IS NULL",
            (LEGACY_DESIGN,),
        )

    conn.commit()


def connect():
    conn = sqlite3.connect(DB_PATH)

    key = str(DB_PATH)
    if key not in _prepared:
        ensure_schema(conn)
        _prepared.add(key)

    return conn


def create_build(commit_hash, branch, timestamp, status, runtime_sec, design=None):
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO builds
            (commit_hash, branch, timestamp, status, runtime_sec, design)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_hash, branch, timestamp, status, runtime_sec, design),
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


def get_previous_corner_timing(build_id, corner, design=None):
    """Timing of the same corner in the most recent earlier build.

    When ``design`` is given only builds of that design are considered, so
    one IP's timing is never compared against another's.
    """
    with connect() as conn:
        if design is None:
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

        return conn.execute(
            """
            SELECT t.setup_wns, t.hold_whs
            FROM timing_results t
            JOIN builds b ON b.id = t.build_id
            WHERE t.build_id < ?
              AND t.corner = ?
              AND b.design = ?
            ORDER BY t.build_id DESC
            LIMIT 1
            """,
            (build_id, corner, design),
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
