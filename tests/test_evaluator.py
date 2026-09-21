# This test verifies evaluation logic without making Gemini API requests.

from agent.schemas import Evidence, FailureAnalysis
from evals.cases import EVAL_CASES
from evals.evaluator import evaluate_result


def get_case(name):
    """Return an evaluation case by name."""
    return next(case for case in EVAL_CASES if case["name"] == name)


def test_simulation_case_passes():
    """Verify a correct simulation failure analysis passes evaluation."""

    case = get_case("simulation_failure")

    result = FailureAnalysis(
        build_id=8,
        status="FAIL",
        summary="Build 8 failed in simulation.",
        failed_stages=["simulation"],
        evidence=[
            Evidence(
                source="get_failed_stages",
                detail="Simulation failed.",
            ),
        ],
        possible_causes=["Simulation failure"],
        recommended_checks=["Inspect simulation logs."],
        confidence="medium",
    )

    assert evaluate_result(result, case) == []


def test_missing_required_evidence_fails():
    """Verify missing evidence is detected."""

    case = get_case("grounded_failure_analysis")

    result = FailureAnalysis(
        build_id=8,
        status="FAIL",
        summary="Build failed.",
        failed_stages=["simulation"],
        evidence=[],
        possible_causes=["Unknown simulation issue"],
        recommended_checks=["Inspect logs."],
        confidence="low",
    )

    failures = evaluate_result(result, case)

    assert "Required evidence source 'builds' is missing." in failures
    assert "Required evidence source 'stage_results' is missing." in failures


def test_missing_build_requires_unknown_status():
    """Verify nonexistent builds must produce UNKNOWN status."""

    case = get_case("missing_build")

    result = FailureAnalysis(
        build_id=999999,
        status="FAIL",
        summary="Build failed.",
        confidence="low",
    )

    failures = evaluate_result(result, case)

    assert "Expected status UNKNOWN, got FAIL." in failures


def test_structured_output_requires_summary():
    """Verify structured-output evaluation requires a meaningful summary."""

    case = get_case("structured_output")

    result = FailureAnalysis(
        build_id=8,
        status="FAIL",
        summary="   ",
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

    failures = evaluate_result(result, case)

    assert "No summary was provided." in failures
