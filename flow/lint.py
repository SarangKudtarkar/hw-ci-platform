import subprocess
import sys
import time
from pathlib import Path


def as_path_list(files):
    """Accept a single path or an iterable of paths."""
    if isinstance(files, (str, Path)):
        return [Path(files)]
    return [Path(f) for f in files]


def run_lint(rtl_files, top_module=None, include_dirs=(), defines=()):
    rtl_files = as_path_list(rtl_files)

    command = ["verilator", "--lint-only"]
    command += [f"-I{d}" for d in include_dirs]
    command += [f"-D{d}" for d in defines]
    if top_module:
        command += ["--top-module", top_module]
    command += [str(f) for f in rtl_files]

    start = time.time()

    result = subprocess.run(
        command,
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
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <rtl_file> [<rtl_file> ...]")
        sys.exit(2)

    result = run_lint(sys.argv[1:])

    print(f"Stage:   {result['stage']}")
    print(f"Status:  {result['status']}")
    print(f"Runtime: {result['runtime_sec']} sec")

    if result["stderr"]:
        print("\nVerilator output:")
        print(result["stderr"])

    sys.exit(result["returncode"])
