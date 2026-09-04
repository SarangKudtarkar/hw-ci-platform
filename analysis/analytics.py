import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "db" / "build.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_build_summary():
    with get_connection() as conn:
        total_builds = conn.execute(
            "SELECT COUNT(*) FROM builds"
        ).fetchone()[0]

        passed_builds = conn.execute(
            "SELECT COUNT(*) FROM builds WHERE status = 'PASS'"
        ).fetchone()[0]

        average_runtime = conn.execute(
            "SELECT AVG(runtime_sec) FROM builds"
        ).fetchone()[0]

    pass_rate = (
        (passed_builds / total_builds) * 100
        if total_builds
        else 0
    )

    return {
        "total_builds": total_builds,
        "passed_builds": passed_builds,
        "pass_rate": round(pass_rate, 2),
        "average_runtime_sec": round(average_runtime, 3)
        if average_runtime is not None
        else 0,
    }


if __name__ == "__main__":
    summary = get_build_summary()

    print("CI BUILD SUMMARY")
    print("=" * 40)
    print(f"Total builds:       {summary['total_builds']}")
    print(f"Passed builds:      {summary['passed_builds']}")
    print(f"Pass rate:          {summary['pass_rate']}%")
    print(f"Average runtime:    {summary['average_runtime_sec']} sec")
