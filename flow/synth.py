import subprocess
import sys
import time
from pathlib import Path


def run_synthesis(rtl_file, top_module):
    rtl_file = Path(rtl_file)

    start = time.time()

    command = [
        "yosys",
        "-p",
        f"read_verilog {rtl_file}; "
        f"hierarchy -top {top_module}; "
        "proc; opt; check; stat",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    runtime = time.time() - start

    return {
        "stage": "synthesis",
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "runtime_sec": round(runtime, 3),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <rtl_file> <top_module>")
        sys.exit(2)

    result = run_synthesis(sys.argv[1], sys.argv[2])

    print(f"Stage:   {result['stage']}")
    print(f"Status:  {result['status']}")
    print(f"Runtime: {result['runtime_sec']} sec")

    if result["stderr"]:
        print("\nYosys output:")
        print(result["stderr"])

    sys.exit(result["returncode"])
