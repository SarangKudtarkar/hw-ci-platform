import subprocess
import sys
import time
from pathlib import Path


def run_simulation(rtl_file, tb_file):
    rtl_file = Path(rtl_file)
    tb_file = Path(tb_file)

    build_dir = Path("results/simulation")
    build_dir.mkdir(parents=True, exist_ok=True)

    executable = build_dir / "sim.out"

    start = time.time()

    compile_result = subprocess.run(
        [
            "iverilog",
            "-o",
            str(executable),
            str(rtl_file),
            str(tb_file),
        ],
        capture_output=True,
        text=True,
    )

    if compile_result.returncode != 0:
        runtime = time.time() - start

        return {
            "stage": "simulation",
            "status": "FAIL",
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

    return {
        "stage": "simulation",
        "status": "PASS" if sim_result.returncode == 0 else "FAIL",
        "runtime_sec": round(runtime, 3),
        "stdout": sim_result.stdout,
        "stderr": sim_result.stderr,
        "returncode": sim_result.returncode,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <rtl_file> <testbench_file>")
        sys.exit(2)

    result = run_simulation(sys.argv[1], sys.argv[2])

    print(f"Stage:   {result['stage']}")
    print(f"Status:  {result['status']}")
    print(f"Runtime: {result['runtime_sec']} sec")

    if result["stdout"]:
        print("\nSimulation output:")
        print(result["stdout"])

    if result["stderr"]:
        print("\nSimulation errors:")
        print(result["stderr"])

    sys.exit(result["returncode"])
