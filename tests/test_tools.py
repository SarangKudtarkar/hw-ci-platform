import pytest

from agent.tools import execute_tool


def test_execute_get_build():
    result = execute_tool("get_build", {"build_id": 8})

    assert result["id"] == 8
    assert result["status"] == "FAIL"


def test_execute_get_stage_results():
    result = execute_tool("get_stage_results", {"build_id": 8})

    assert len(result) > 0
    assert all(stage["build_id"] == 8 for stage in result)


def test_execute_get_failed_stages():
    result = execute_tool("get_failed_stages", {"build_id": 8})

    assert len(result) > 0
    assert all(stage["status"] == "FAIL" for stage in result)


def test_execute_get_recent_failures():
    result = execute_tool("get_recent_failures", {"limit": 3})

    assert len(result) <= 3
    assert all(build["status"] == "FAIL" for build in result)


def test_execute_get_timing_results():
    result = execute_tool("get_timing_results", {"build_id": 11})

    assert len(result) == 3
    assert all(row["build_id"] == 11 for row in result)


def test_execute_get_missing_build():
    result = execute_tool("get_build", {"build_id": 999999})

    assert "error" in result


def test_execute_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        execute_tool("delete_database", {})
