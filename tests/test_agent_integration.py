# This test verifies the complete agent flow against the real Gemini API.

import os

import pytest

from agent.agent import analyze_build_with_agent


@pytest.mark.integration
def test_real_gemini_agent_analyzes_build():
    """Verify Gemini can analyze a real CI build through controlled tools."""

    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY is not set.")

    result = analyze_build_with_agent(8)

    assert result.build_id == 8
    assert result.status == "FAIL"
    assert "simulation" in result.failed_stages
    assert result.evidence
    assert result.possible_causes
    assert result.recommended_checks
