# This module implements the bounded Gemini agent loop with controlled CI tool calling.

import json
import os

from google import genai

from agent.schemas import FailureAnalysis
from agent.tools import CI_TOOLS, execute_tool

SYSTEM_PROMPT = """
You are a hardware CI failure-analysis agent.

Analyze hardware CI builds using only the controlled tools provided to you.

Rules:
- Gather all relevant evidence using the available CI tools before analyzing the build.
- You may request multiple CI tools in your first turn.
- Do not invent engineering evidence.
- Treat possible causes as hypotheses unless directly supported by evidence.
- Focus on failed stages, concrete evidence, possible causes, and recommended engineering checks.
- After receiving the tool results, return the final failure analysis.
- Do not request additional tools after receiving the tool results.
- Return a failure analysis matching the requested schema.
"""

MAX_AGENT_CALLS = 2


def _extract_output_text(interaction) -> str:
    """Extract final model text from an Interactions API response."""

    if interaction.output_text:
        return interaction.output_text

    for step in reversed(interaction.steps):
        if step.type != "model_output":
            continue

        for content in step.content:
            if getattr(content, "type", None) == "text":
                return content.text

    return ""


def analyze_build_with_agent(build_id: int) -> FailureAnalysis:
    """Analyze a CI build using at most two Gemini requests."""

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    client = genai.Client(api_key=api_key)

    interaction = client.interactions.create(
        model=model,
        store=True,
        system_instruction=SYSTEM_PROMPT,
        input=(
            f"Analyze hardware CI build {build_id}. "
            "Use all relevant CI tools needed to gather the evidence "
            "before producing the final analysis."
        ),
        tools=CI_TOOLS,
    )

    function_calls = [
        step
        for step in interaction.steps
        if step.type == "function_call"
    ]

    if not function_calls:
        output_text = _extract_output_text(interaction)

        if not output_text:
            raise RuntimeError(
                f"Gemini returned no final text. "
                f"status={interaction.status!r}, "
                f"steps={[step.type for step in interaction.steps]!r}"
            )

        return FailureAnalysis.model_validate_json(output_text)

    function_results = []

    for call in function_calls:
        result = execute_tool(
            call.name,
            call.arguments,
        )

        function_results.append(
            {
                "type": "function_result",
                "name": call.name,
                "call_id": call.id,
                "result": [
                    {
                        "type": "text",
                        "text": json.dumps(result),
                    }
                ],
            }
        )

    if MAX_AGENT_CALLS < 2:
        raise RuntimeError("Agent call budget is too small.")

    interaction = client.interactions.create(
        model=model,
        store=True,
        previous_interaction_id=interaction.id,
        input=function_results,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": FailureAnalysis.model_json_schema(),
        },
    )

    output_text = _extract_output_text(interaction)

    if not output_text:
        raise RuntimeError(
            f"Gemini did not return a final analysis within the "
            f"{MAX_AGENT_CALLS}-request limit. "
            f"status={interaction.status!r}, "
            f"steps={[step.type for step in interaction.steps]!r}"
        )

    return FailureAnalysis.model_validate_json(output_text)
