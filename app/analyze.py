# This module provides the engineer-facing CLI for CI failure analysis.

import argparse
import json
import sys

from agent.agent import analyze_build_with_agent


def main(argv: list[str] | None = None) -> int:
    """Run CI failure analysis for a build ID."""

    parser = argparse.ArgumentParser(
        description="Analyze a hardware CI build with the Gemini agent.",
    )
    parser.add_argument(
        "build_id",
        type=int,
        help="CI build ID to analyze.",
    )

    args = parser.parse_args(argv)

    try:
        result = analyze_build_with_agent(args.build_id)
    except Exception as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
