# This test file verifies that the AI failure-analysis output contract accepts valid data and rejects invalid values.

import pytest
from pydantic import ValidationError

from agent.schemas import Evidence, FailureAnalysis


def test_failure_analysis_valid():
    # This test verifies that a valid failure-analysis report can be created.
    report = FailureAnalysis(
        build_id=8,
        status="FAIL",
        summary="Simulation failed.",
        failed_stages=["simulation"],
        evidence=[
            Evidence(
                source="stage_results",
                detail="Simulation stage failed.",
            )
        ],
        possible_causes=["Simulation test failure"],
        recommended_checks=["Inspect simulation output."],
        confidence="medium",
    )

    assert report.build_id == 8
    assert report.status == "FAIL"
    assert report.failed_stages == ["simulation"]
    assert report.confidence == "medium"


def test_failure_analysis_rejects_invalid_status():
    # This test verifies that unsupported status values are rejected.
    with pytest.raises(ValidationError):
        FailureAnalysis(
            build_id=8,
            status="BROKEN",
            summary="Simulation failed.",
            confidence="medium",
        )


def test_failure_analysis_rejects_invalid_confidence():
    # This test verifies that unsupported confidence values are rejected.
    with pytest.raises(ValidationError):
        FailureAnalysis(
            build_id=8,
            status="FAIL",
            summary="Simulation failed.",
            confidence="certain",
        )
