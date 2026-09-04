import subprocess
import sys
import time
from pathlib import Path


def run_lint(rtl_file):
    rtl_file = Path(rtl_file)

    start = time.time()

    result = subprocess.run(
        ["verilator", "--lint-only", str(rtl_file)],
        capture_output=True,
        text=True,
    )

    runtime = time.time() - start

    return {
        "stage": "lint",
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "runtime_sec": round(runtime, 3),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <rtl_file>")
        sys.exit(2)

    result = run_lint(sys.argv[1])

    print(f"Stage:   {result['stage']}")
    print(f"Status:  {result['status']}")
    print(f"Runtime: {result['runtime_sec']} sec")

    if result["stderr"]:
        print("\nVerilator output:")
        print(result["stderr"])

    sys.exit(result["returncode"])
