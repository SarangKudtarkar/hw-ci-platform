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


def get_timing():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                t.build_id,
                t.corner,
                b.commit_hash,
                b.timestamp,
                t.setup_wns,
                t.hold_whs
            FROM timing_results t
            JOIN builds b ON b.id = t.build_id
            ORDER BY t.build_id, t.id
            """,
            conn,
        )


st.set_page_config(
    page_title="HW-CI Health Dashboard",
    page_icon="🏗️",
    layout="wide",
)

st.markdown("""
<style>
    html, body, [class*="css"], .stApp {
        font-family: "Segoe UI", Arial, sans-serif;
    }

    h1 {
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    h2 {
        font-size: 1.8rem;
        font-weight: 650;
        margin-top: 1.8rem;
    }

    h3 {
        font-size: 1.5rem;
        font-weight: 650;
    }

    p {
        font-size: 18px;
    }

    [data-testid="stMetric"] {
        padding: 12px 8px;
    }

    [data-testid="stMetricLabel"] {
        font-size: 17px;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        font-size: 2.7rem;
        font-weight: 700;
        line-height: 1.2;
    }

    [data-testid="stDataFrame"] {
        font-size: 17px;
    }

    .stCaption {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)


st.title("HW-CI Health Dashboard")
st.caption("Build health, MMMC timing closure, and regression analytics")

builds = get_builds()
timing = get_timing()

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


if not timing.empty:
    latest_build_id = timing["build_id"].max()
    latest_timing = timing[timing["build_id"] == latest_build_id].copy()

    worst_setup = latest_timing.loc[
        latest_timing["setup_wns"].idxmin()
    ]

    worst_hold = latest_timing.loc[
        latest_timing["hold_whs"].idxmin()
    ]

    st.subheader(f"Latest MMMC Timing — Build {latest_build_id}")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Worst Setup WNS",
        f"{worst_setup['setup_wns']:.2f} ns",
    )

    col2.metric(
        "Setup Corner",
        str(worst_setup["corner"]),
    )

    col3.metric(
        "Worst Hold WHS",
        f"{worst_hold['hold_whs']:.2f} ns",
    )

    col4.metric(
        "Hold Corner",
        str(worst_hold["corner"]),
    )

    if worst_setup["setup_wns"] >= 0 and worst_hold["hold_whs"] >= 0:
        st.success("MMMC Timing Closure: PASS")
    else:
        st.error("MMMC Timing Closure: FAIL")

    st.subheader("Latest Corner Analysis")

    latest_display = latest_timing[
        ["corner", "setup_wns", "hold_whs"]
    ].copy()

    latest_display["setup_wns"] = latest_display["setup_wns"].round(3)
    latest_display["hold_whs"] = latest_display["hold_whs"].round(3)

    st.dataframe(
        latest_display,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("MMMC Timing Trend")

    trend = timing.pivot_table(
        index="build_id",
        columns="corner",
        values="setup_wns",
        aggfunc="first",
    )

    st.line_chart(trend)

    st.subheader("Timing History")

    display_timing = timing.copy()
    display_timing["commit_hash"] = (
        display_timing["commit_hash"].str[:8]
    )
    display_timing["setup_wns"] = display_timing["setup_wns"].round(3)
    display_timing["hold_whs"] = display_timing["hold_whs"].round(3)

    st.dataframe(
        display_timing[
            [
                "build_id",
                "corner",
                "commit_hash",
                "timestamp",
                "setup_wns",
                "hold_whs",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


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
