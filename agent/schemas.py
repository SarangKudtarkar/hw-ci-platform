from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source: str = Field(
        description="Source of the engineering evidence."
    )
    detail: str = Field(
        description="Specific evidence supporting the analysis."
    )


class FailureAnalysis(BaseModel):
    build_id: int

    status: Literal["PASS", "FAIL", "UNKNOWN"]

    summary: str

    failed_stages: list[str] = Field(
        default_factory=list
    )

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    possible_causes: list[str] = Field(
        default_factory=list
    )

    recommended_checks: list[str] = Field(
        default_factory=list
    )

    confidence: Literal["low", "medium", "high"]
