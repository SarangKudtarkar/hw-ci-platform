# This module provides the Gemini LLM interface used by the failure-analysis agent.

import json
import os
from typing import Any

from google import genai

from agent.schemas import FailureAnalysis


SYSTEM_PROMPT = """
You are a hardware CI failure-analysis assistant.

Analyze only the engineering evidence provided to you.

Do not invent evidence.
Do not claim certainty when the evidence is insufficient.
Return only valid JSON matching the requested failure-analysis schema.

Focus on:
- identifying failed CI stages,
- citing concrete evidence,
- proposing plausible causes,
- recommending useful engineering checks.
"""


def analyze_with_llm(evidence: dict[str, Any]) -> FailureAnalysis:
    """Send controlled CI evidence to Gemini and return validated analysis."""

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3-flash"),
        contents=(
            f"{SYSTEM_PROMPT}\n\n"
            f"Engineering evidence:\n"
            f"{json.dumps(evidence, indent=2)}"
        ),
        config={
            "response_mime_type": "application/json",
            "response_schema": FailureAnalysis.model_json_schema(),
        },
    )

    return FailureAnalysis.model_validate_json(response.text)
