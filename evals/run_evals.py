# This module runs the AI evaluation cases sequentially.

import time

from agent.agent import analyze_build_with_agent
from evals.cases import EVAL_CASES
from evals.evaluator import evaluate_result


def main() -> None:
    """Run all evaluation cases sequentially."""

    total = len(EVAL_CASES)
    passed = 0

    for index, case in enumerate(EVAL_CASES, start=1):
        print(f"\n[{index}/{total}] {case['name']}")

        try:
            result = analyze_build_with_agent(case["build_id"])
            failures = evaluate_result(result, case)

            if failures:
                print("FAIL")
                for failure in failures:
                    print(f"  - {failure}")
            else:
                passed += 1
                print("PASS")

        except Exception as exc:
            print("ERROR")
            print(f"  - {exc}")

        if index < total:
            time.sleep(5)

    print(f"\nEvaluation result: {passed}/{total} passed.")


if __name__ == "__main__":
    main()
