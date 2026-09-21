# This module collects controlled CI evidence for the failure-analysis agent.

from typing import Any

from tools.ci_tools import (
    get_build,
    get_failed_stages,
    get_stage_results,
    get_timing_results,
)


def collect_build_evidence(build_id: int) -> dict[str, Any]:
    """Collect the CI evidence needed to analyze one build."""

    build = get_build(build_id)

    if build is None:
        raise ValueError(f"Build {build_id} was not found.")

    return {
        "build": build,
        "stage_results": get_stage_results(build_id),
        "failed_stages": get_failed_stages(build_id),
        "timing_results": get_timing_results(build_id),
    }
