import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess
import time
from datetime import datetime, timezone

from lint import run_lint
from synth import run_synthesis
from simulate import run_simulation
from mmmc_sta import run_mmmc_sta

from db.database import create_build, create_stage_result, create_timing_result, get_previous_corner_timing


def get_git_metadata(repo_path):
    branch = subprocess.check_output(
        ["git", "-C", repo_path, "branch", "--show-current"],
        text=True,
    ).strip()

    commit = subprocess.check_output(
        ["git", "-C", repo_path, "rev-parse", "HEAD"],
        text=True,
    ).strip()

    return branch, commit


def run_pipeline(rtl_file, tb_file, top_module, repo_path):
    pipeline_start = time.time()

    repo_path = Path(repo_path).resolve()

    branch, commit_hash = get_git_metadata(repo_path)

    results = []

    print("=" * 60)
    print("HW-CI PIPELINE")
    print("=" * 60)

    print(f"\nBranch: {branch}")
    print(f"Commit: {commit_hash}")

    print("\n[1/4] Running lint...")
    lint_result = run_lint(rtl_file)
    results.append(lint_result)
    print(
        f"       {lint_result['status']} "
        f"({lint_result['runtime_sec']} sec)"
    )

    if lint_result["returncode"] != 0:
        print("\nPipeline stopped: lint failed.")

    else:
        print("\n[2/4] Running synthesis...")
        synth_result = run_synthesis(rtl_file, top_module)
        results.append(synth_result)
        print(
            f"       {synth_result['status']} "
            f"({synth_result['runtime_sec']} sec)"
        )

        if synth_result["returncode"] != 0:
            print("\nPipeline stopped: synthesis failed.")

        else:
            print("\n[3/4] Running simulation...")
            sim_result = run_simulation(rtl_file, tb_file)
            results.append(sim_result)
            print(
                f"       {sim_result['status']} "
                f"({sim_result['runtime_sec']} sec)"
            )

            if sim_result["returncode"] != 0:
                print("\nPipeline stopped: simulation failed.")

            else:
                sta_netlist = (
                    repo_path
                    / "results"
                    / "routing"
                    / f"{top_module}.nl.v"
                )

                sta_sdc = (
                    repo_path
                    / "src"
                    / f"{top_module}.sdc"
                )

                sta_spef = (
                    repo_path
                    / "results"
                    / "routing"
                    / "mca"
                    / "spef"
                    / f"{top_module}.nom.spef"
                )

                print("\n[4/4] Running MMMC STA...")

                mmmc_results, mmmc_status = run_mmmc_sta(
                    netlist=sta_netlist,
                    sdc=sta_sdc,
                    spef=sta_spef,
                    top_module=top_module,
                )

                for mmmc_result in mmmc_results:
                    results.append({
                        "stage": "sta",
                        "status": mmmc_result["status"],
                        "runtime_sec": mmmc_result["runtime_sec"],
                        "corner": mmmc_result["corner"],
                        "setup_wns": mmmc_result["setup_wns"],
                        "hold_whs": mmmc_result["hold_whs"],
                    })

                print(f"       MMMC Timing closure: {mmmc_status}")




    pipeline_runtime = time.time() - pipeline_start

    overall_status = (
        "PASS"
        if all(result["status"] == "PASS" for result in results)
        else "FAIL"
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    build_id = create_build(
        commit_hash,
        branch,
        timestamp,
        overall_status,
        round(pipeline_runtime, 3),
    )

    for result in results:
        if result["stage"] == "sta":
            corner = result["corner"]
            previous = get_previous_corner_timing(build_id, corner)

            if previous is not None:
                previous_setup, previous_hold = previous

                setup_delta = result["setup_wns"] - previous_setup
                hold_delta = result["hold_whs"] - previous_hold

                print(
                    f"       {corner} regression: "
                    f"setup {setup_delta:+.2f} ns, "
                    f"hold {hold_delta:+.2f} ns"
                )

    for result in results:
        create_stage_result(
            build_id,
            result["stage"],
            result["status"],
            result["runtime_sec"],
        )

        if result["stage"] == "sta":
            create_timing_result(
                build_id,
                result["corner"],
                result["setup_wns"],
                result["hold_whs"],
            )

    print("\n" + "=" * 60)
    print(f"PIPELINE: {overall_status}")
    print(f"TOTAL RUNTIME: {pipeline_runtime:.3f} sec")
    print(f"BUILD ID: {build_id}")
    print("=" * 60)

    return results, overall_status


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            f"Usage: python {sys.argv[0]} "
            "<rtl_file> <testbench_file> <top_module> <repo_path>"
        )
        sys.exit(2)

    results, overall_status = run_pipeline(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
    )

    sys.exit(0 if overall_status == "PASS" else 1)
