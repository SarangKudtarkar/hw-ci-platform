# This test verifies the engineer-facing CLI without making Gemini API requests.

import json

from agent.schemas import Evidence, FailureAnalysis
from app import analyze


def test_cli_prints_analysis(monkeypatch, capsys):
    """Verify the CLI prints a validated failure analysis."""

    result = FailureAnalysis(
        build_id=8,
        status="FAIL",
        summary="Build 8 failed in simulation.",
        failed_stages=["simulation"],
        evidence=[
            Evidence(
                source="stage_results",
                detail="Simulation failed.",
            ),
        ],
        possible_causes=["Simulation failure"],
        recommended_checks=["Inspect simulation logs."],
        confidence="medium",
    )

    monkeypatch.setattr(
        analyze,
        "analyze_build_with_agent",
        lambda build_id: result,
    )

    exit_code = analyze.main(["8"])

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["build_id"] == 8
    assert output["status"] == "FAIL"
    assert output["failed_stages"] == ["simulation"]


def test_cli_returns_error_on_agent_failure(monkeypatch, capsys):
    """Verify the CLI returns a non-zero code when analysis fails."""

    monkeypatch.setattr(
        analyze,
        "analyze_build_with_agent",
        lambda build_id: (_ for _ in ()).throw(
            RuntimeError("Gemini unavailable"),
        ),
    )

    exit_code = analyze.main(["8"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Analysis failed: Gemini unavailable" in captured.err
