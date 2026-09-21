# This test file verifies the deterministic CI failure analyzer.

from agent.analyzer import analyze_build


def test_analyze_failed_build():
    # This test verifies that a known failed build produces the expected diagnosis.
    report = analyze_build(8)

    assert report.build_id == 8
    assert report.status == "FAIL"
    assert "simulation" in report.failed_stages
    assert len(report.evidence) > 0
    assert len(report.possible_causes) > 0
    assert len(report.recommended_checks) > 0


def test_analyze_passing_build():
    # This test verifies that a successful build produces a PASS analysis.
    report = analyze_build(11)

    assert report.build_id == 11
    assert report.status == "PASS"
    assert report.confidence == "high"
