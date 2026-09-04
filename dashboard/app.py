import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).parent.parent / "db" / "build.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_builds():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                id,
                commit_hash,
                branch,
                timestamp,
                status,
                runtime_sec
            FROM builds
            ORDER BY id
            """,
            conn,
        )


st.set_page_config(
    page_title="HW-CI Health Dashboard",
    page_icon="🏗️",
    layout="wide",
)

st.title("HW-CI Health Dashboard")
st.caption("Build health and runtime analytics for hardware repositories")

builds = get_builds()

if builds.empty:
    st.warning("No CI builds found.")
    st.stop()

total_builds = len(builds)
passed_builds = len(builds[builds["status"] == "PASS"])
failed_builds = len(builds[builds["status"] == "FAIL"])
pass_rate = (passed_builds / total_builds) * 100
average_runtime = builds["runtime_sec"].mean()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Builds", total_builds)
col2.metric("Passed Builds", passed_builds)
col3.metric("Failed Builds", failed_builds)
col4.metric("Pass Rate", f"{pass_rate:.1f}%")

st.divider()

if failed_builds == 0:
    st.success("Pipeline Health: HEALTHY")
else:
    st.error(f"Pipeline Health: {failed_builds} failed build(s) detected")

st.subheader("Build Runtime Trend")

chart_data = builds.set_index("id")[["runtime_sec"]]
st.line_chart(chart_data)

st.subheader("Build History")

display_builds = builds.copy()
display_builds["commit_hash"] = display_builds["commit_hash"].str[:8]

st.dataframe(
    display_builds,
    use_container_width=True,
    hide_index=True,
)

st.caption(f"Average pipeline runtime: {average_runtime:.3f} seconds")
