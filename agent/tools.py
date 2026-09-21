# This module defines the read-only CI tools that Gemini is allowed to request.

from tools.ci_tools import (
    get_build,
    get_failed_stages,
    get_recent_failures,
    get_stage_results,
    get_timing_results,
)


CI_TOOLS = [
    {
        "type": "function",
        "name": "get_build",
        "description": "Return metadata and status for a specific hardware CI build.",
        "parameters": {
            "type": "object",
            "properties": {
                "build_id": {
                    "type": "integer",
                    "description": "The CI build ID to inspect.",
                }
            },
            "required": ["build_id"],
        },
    },
    {
        "type": "function",
        "name": "get_stage_results",
        "description": "Return all CI stage results for a specific build.",
        "parameters": {
            "type": "object",
            "properties": {
                "build_id": {
                    "type": "integer",
                    "description": "The CI build ID to inspect.",
                }
            },
            "required": ["build_id"],
        },
    },
    {
        "type": "function",
        "name": "get_failed_stages",
        "description": "Return only the failed CI stages for a specific build.",
        "parameters": {
            "type": "object",
            "properties": {
                "build_id": {
                    "type": "integer",
                    "description": "The CI build ID to inspect.",
                }
            },
            "required": ["build_id"],
        },
    },
    {
        "type": "function",
        "name": "get_recent_failures",
        "description": "Return recent failed hardware CI builds.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of failed builds to return.",
                }
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_timing_results",
        "description": "Return timing results for a specific hardware CI build.",
        "parameters": {
            "type": "object",
            "properties": {
                "build_id": {
                    "type": "integer",
                    "description": "The CI build ID to inspect.",
                }
            },
            "required": ["build_id"],
        },
    },
]


def execute_tool(name: str, arguments: dict) -> dict | list:
    """Execute one approved read-only CI tool."""

    if name == "get_build":
        result = get_build(arguments["build_id"])
        return result if result is not None else {
            "error": f"Build {arguments['build_id']} was not found."
        }

    if name == "get_stage_results":
        return get_stage_results(arguments["build_id"])

    if name == "get_failed_stages":
        return get_failed_stages(arguments["build_id"])

    if name == "get_recent_failures":
        limit = arguments.get("limit", 10)
        return get_recent_failures(limit)

    if name == "get_timing_results":
        return get_timing_results(arguments["build_id"])

    raise ValueError(f"Unknown tool: {name}")
