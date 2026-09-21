from tools.ci_tools import (
    get_build,
    get_stage_results,
    get_failed_stages,
    get_recent_failures,
    get_timing_results,
)


def test_get_build():
    build = get_build(11)

    assert build is not None
    assert build["id"] == 11
    assert build["status"] == "PASS"
    assert build["branch"] == "main"


def test_get_nonexistent_build():
    build = get_build(999999)

    assert build is None


def test_get_stage_results():
    stages = get_stage_results(8)

    assert len(stages) > 0
    assert all(stage["build_id"] == 8 for stage in stages)


def test_get_failed_stages():
    failures = get_failed_stages(8)

    assert len(failures) > 0
    assert all(stage["status"] == "FAIL" for stage in failures)
    assert any(stage["stage"] == "simulation" for stage in failures)


def test_get_recent_failures():
    failures = get_recent_failures()

    assert len(failures) > 0
    assert all(build["status"] == "FAIL" for build in failures)


def test_get_timing_results():
    timing = get_timing_results(11)

    assert len(timing) == 3
    assert all(result["build_id"] == 11 for result in timing)
    assert all("corner" in result for result in timing)
