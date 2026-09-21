# This module converts collected CI evidence into a structured failure analysis.

from agent.evidence import collect_build_evidence
from agent.schemas import Evidence, FailureAnalysis


def analyze_build(build_id: int) -> FailureAnalysis:
    """Analyze one CI build using its collected engineering evidence."""

    evidence = collect_build_evidence(build_id)

    build = evidence["build"]
    failed_stages = evidence["failed_stages"]

    if build["status"] == "PASS":
        return FailureAnalysis(
            build_id=build_id,
            status="PASS",
            summary="Build completed successfully.",
            confidence="high",
        )

    failed_stage_names = [
        stage["stage"]
        for stage in failed_stages
    ]

    evidence_items = [
        Evidence(
            source="builds",
            detail=f"Build status is {build['status']}.",
        )
    ]

    for stage in failed_stages:
        evidence_items.append(
            Evidence(
                source="stage_results",
                detail=(
                    f"Stage '{stage['stage']}' failed "
                    f"with runtime {stage['runtime_sec']} seconds."
                ),
            )
        )

    possible_causes = [
        f"Failure in stage: {stage}"
        for stage in failed_stage_names
    ]

    recommended_checks = [
        f"Inspect logs and test output for the '{stage}' stage."
        for stage in failed_stage_names
    ]

    summary = (
        f"Build {build_id} failed in "
        f"{', '.join(failed_stage_names)}."
    )

    return FailureAnalysis(
        build_id=build_id,
        status="FAIL",
        summary=summary,
        failed_stages=failed_stage_names,
        evidence=evidence_items,
        possible_causes=possible_causes,
        recommended_checks=recommended_checks,
        confidence="medium",
    )
