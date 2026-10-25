import re
import subprocess
import sys
import time
from pathlib import Path

from lint import as_path_list

# Same default as design_config.DEFAULT_SIM_FAIL_REGEX (kept literal so this
# script still runs standalone).
DEFAULT_FAIL_REGEX = r"\b(ERROR|FAIL|FAILED|MISMATCH)\b"


def judge(returncode, output, pass_regex=None, fail_regex=DEFAULT_FAIL_REGEX):
    """Decide PASS/FAIL for a finished simulation.

    A testbench that prints a failure and then calls $finish still exits 0, so
    the exit code is combined with the output: no fail marker may appear and,
    if a pass marker is configured, it must appear.
    """
    if returncode != 0:
        return "FAIL", f"simulator exited with code {returncode}"

    if fail_regex:
        match = re.search(fail_regex, output)
        if match:
            line = next(
                (ln.strip() for ln in output.splitlines() if match.group(0) in ln),
                match.group(0),
            )
            return "FAIL", f"failure marker in output: {line}"

    if pass_regex and not re.search(pass_regex, output):
        return "FAIL", f"pass marker /{pass_regex}/ not found in output"

    return "PASS", ""


def run_simulation(
    rtl_files,
    tb_file,
    build_dir="results/simulation",
    include_dirs=(),
    defines=(),
    tb_top=None,
    pass_regex=None,
    fail_regex=DEFAULT_FAIL_REGEX,
):
    rtl_files = as_path_list(rtl_files)
    tb_file = Path(tb_file)

    build_dir = Path(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    executable = build_dir / "sim.out"

    command = ["iverilog", "-o", str(executable)]
    command += [f"-I{d}" for d in include_dirs]
    command += [f"-D{d}" for d in defines]
    if tb_top:
        command += ["-s", tb_top]
    command += [str(f) for f in rtl_files] + [str(tb_file)]

    start = time.time()

    compile_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if compile_result.returncode != 0:
        runtime = time.time() - start

        return {
            "stage": "simulation",
            "status": "FAIL",
            "detail": "compile error",
            "runtime_sec": round(runtime, 3),
            "stdout": compile_result.stdout,
            "stderr": compile_result.stderr,
            "returncode": compile_result.returncode,
        }

    sim_result = subprocess.run(
        [str(executable)],
        capture_output=True,
        text=True,
    )

    runtime = time.time() - start

    status, detail = judge(
        sim_result.returncode,
        sim_result.stdout + "\n" + sim_result.stderr,
        pass_regex,
        fail_regex,
    )

    return {
        "stage": "simulation",
        "status": status,
        "detail": detail,
        "runtime_sec": round(runtime, 3),
        "stdout": sim_result.stdout,
        "stderr": sim_result.stderr,
        # A failure found in the output must still read as non-zero.
        "returncode": 0 if status == "PASS" else (sim_result.returncode or 1),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            f"Usage: python {sys.argv[0]} <rtl_file> [<rtl_file> ...] <testbench_file>"
        )
        sys.exit(2)

    result = run_simulation(sys.argv[1:-1], sys.argv[-1])

    print(f"Stage:   {result['stage']}")
    print(f"Status:  {result['status']}")
    print(f"Runtime: {result['runtime_sec']} sec")

    if result.get("detail"):
        print(f"Reason:  {result['detail']}")

    if result["stdout"]:
        print("\nSimulation output:")
        print(result["stdout"])

    if result["stderr"]:
        print("\nSimulation errors:")
        print(result["stderr"])

    sys.exit(result["returncode"])
