# This test verifies that LLM output is converted into the required structured schema.

from agent.schemas import FailureAnalysis


def test_llm_output_schema():
    # This test simulates the structured output that an LLM should produce.
    raw_output = """
    {
      "build_id": 8,
      "status": "FAIL",
      "summary": "Build 8 failed during simulation.",
      "failed_stages": ["simulation"],
      "evidence": [
        {
          "source": "stage_results",
          "detail": "Simulation stage failed."
        }
      ],
      "possible_causes": [
        "Simulation test failure"
      ],
      "recommended_checks": [
        "Inspect simulation logs and test output."
      ],
      "confidence": "medium"
    }
    """

    result = FailureAnalysis.model_validate_json(raw_output)

    assert result.build_id == 8
    assert result.status == "FAIL"
    assert "simulation" in result.failed_stages
