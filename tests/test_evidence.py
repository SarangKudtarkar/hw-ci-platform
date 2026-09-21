# This test file verifies that the agent collects the expected CI evidence.

import pytest

from agent.evidence import collect_build_evidence


def test_collect_build_evidence():
    # This test verifies that a real build produces a complete evidence package.
    evidence = collect_build_evidence(8)

    assert evidence["build"]["id"] == 8
    assert len(evidence["stage_results"]) > 0
    assert len(evidence["failed_stages"]) > 0
    assert any(
        stage["stage"] == "simulation"
        for stage in evidence["failed_stages"]
    )


def test_collect_build_evidence_missing_build():
    # This test verifies that an unknown build produces a clear error.
    with pytest.raises(ValueError, match="Build 999999 was not found"):
        collect_build_evidence(999999)
