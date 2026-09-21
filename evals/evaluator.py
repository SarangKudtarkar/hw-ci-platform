# This module validates agent outputs against deterministic engineering expectations.

from agent.schemas import FailureAnalysis


EVIDENCE_SOURCE_ALIASES = {
    "stage_results": {"stage_results", "get_stage_results", "get_failed_stages"},
    "builds": {"builds", "get_build"},
    "timing_results": {"timing_results", "get_timing_results"},
}


def evaluate_result(
    result: FailureAnalysis,
    case: dict,
) -> list[str]:
    """Return evaluation failures for one agent result."""

    failures = []

    expected_status = case["expected_status"]

    if expected_status is not None and result.status != expected_status:
        failures.append(
            f"Expected status {expected_status}, got {result.status}."
        )

    expected_stage = case["expected_failed_stage"]

    if expected_stage is not None:
        if expected_stage not in result.failed_stages:
            failures.append(
                f"Expected failed stage '{expected_stage}' was not reported."
            )

    sources = {item.source for item in result.evidence}

    for required_source in case["required_evidence"]:
        accepted_sources = EVIDENCE_SOURCE_ALIASES.get(
            required_source,
            {required_source},
        )

        if not sources.intersection(accepted_sources):
            failures.append(
                f"Required evidence source '{required_source}' is missing."
            )

    if case["requires_causes"] and not result.possible_causes:
        failures.append("No possible causes were provided.")

    if case["requires_checks"] and not result.recommended_checks:
        failures.append("No recommended engineering checks were provided.")

    if case.get("requires_summary") and not result.summary.strip():
        failures.append("No summary was provided.")

    return failures
