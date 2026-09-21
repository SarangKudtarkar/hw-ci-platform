# This test verifies the Gemini agent loop without making real API requests.

import json

from agent.agent import analyze_build_with_agent


class FakeStep:
    """Represent a minimal Gemini function-call step."""

    def __init__(self, name, arguments, step_id):
        self.type = "function_call"
        self.name = name
        self.arguments = arguments
        self.id = step_id


class FakeInteraction:
    """Represent a minimal Gemini interaction response."""

    def __init__(self, steps=None, output_text=""):
        self.steps = steps or []
        self.output_text = output_text
        self.id = "fake-interaction"


class FakeInteractions:
    """Simulate the Gemini Interactions API."""

    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if len(self.calls) == 1:
            return FakeInteraction(
                steps=[
                    FakeStep(
                        name="get_failed_stages",
                        arguments={"build_id": 8},
                        step_id="call-1",
                    )
                ]
            )

        result = {
            "build_id": 8,
            "status": "FAIL",
            "summary": "Build 8 failed in simulation.",
            "failed_stages": ["simulation"],
            "evidence": [
                {
                    "source": "stage_results",
                    "detail": "Stage 'simulation' failed with runtime 0.011 seconds.",
                }
            ],
            "possible_causes": [
                "Testbench assertion failure",
            ],
            "recommended_checks": [
                "Inspect simulation logs and testbench output.",
            ],
            "confidence": "medium",
        }

        return FakeInteraction(
            output_text=json.dumps(result)
        )


class FakeClient:
    """Simulate the Gemini client."""

    def __init__(self):
        self.interactions = FakeInteractions()


def test_agent_uses_at_most_two_gemini_requests(monkeypatch):
    """Verify the agent completes using no more than two model requests."""

    fake_client = FakeClient()

    monkeypatch.setattr(
        "agent.agent.genai.Client",
        lambda api_key: fake_client,
    )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    result = analyze_build_with_agent(8)

    assert result.build_id == 8
    assert result.status == "FAIL"
    assert "simulation" in result.failed_stages
    assert len(result.evidence) > 0

    assert len(fake_client.interactions.calls) == 2


def test_agent_passes_tool_result_to_second_request(monkeypatch):
    """Verify the second request continues from the first interaction."""

    fake_client = FakeClient()

    monkeypatch.setattr(
        "agent.agent.genai.Client",
        lambda api_key: fake_client,
    )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    analyze_build_with_agent(8)

    first_call = fake_client.interactions.calls[0]
    second_call = fake_client.interactions.calls[1]

    assert "tools" in first_call
    assert second_call["previous_interaction_id"] == "fake-interaction"
    assert len(second_call["input"]) == 1
    assert second_call["input"][0]["type"] == "function_result"
    assert second_call["input"][0]["name"] == "get_failed_stages"
