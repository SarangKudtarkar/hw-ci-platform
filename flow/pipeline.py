import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The flow modules import each other by bare name (they are normally run as
# scripts from flow/), and db/ is imported from the project root.
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import argparse
import subprocess
import time
from datetime import datetime, timezone

from design_config import DesignError, legacy_design, resolve_design
from lint import run_lint
from synth import run_synthesis
from simulate import run_simulation
from mmmc_sta import run_mmmc_sta

from db.database import create_build, create_stage_result, create_timing_result, get_previous_corner_timing


def get_git_metadata(repo_path):
    """Branch and commit of the input repository; 'unknown' if it is not git."""

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(repo_path), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

    try:
        return git("branch", "--show-current"), git("rev-parse", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "unknown"


def print_failure_output(result, max_lines=20):
    """Show the tail of a failed stage's output so the CI console is useful."""
    if result.get("detail"):
        print(f"       reason: {result['detail']}")

    text = (result.get("stderr") or "") + (result.get("stdout") or "")
    lines = [line for line in text.splitlines() if line.strip()]

    for line in lines[-max_lines:]:
        print(f"       | {line}")


def run_sta_stage(design, results):
    if design.sta_mode == "skip":
        print("\n[4/4] MMMC STA skipped (mode: skip)")
        return

    missing = design.missing_sta_inputs()

    if missing and design.sta_mode == "auto":
        print(
            "\n[4/4] MMMC STA skipped: no routed netlist / SDC / SPEF "
            "for this design. Provide them (see [sta] in hwci.toml) or "
            "run the design through OpenLane first."
        )
        for path in missing:
            print(f"       missing: {path}")
        return

    for path in missing:
        print(f"       missing STA input: {path}")

    print("\n[4/4] Running MMMC STA...")

    mmmc_results, mmmc_status = run_mmmc_sta(
        netlist=design.sta_netlist,
        sdc=design.sta_sdc,
        spef=design.sta_spef,
        top_module=design.top,
        output_dir=PROJECT_ROOT / "results" / design.name / "mmmc_sta",
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


def run_design_pipeline(design):
    pipeline_start = time.time()

    branch, commit_hash = get_git_metadata(design.repo_path)

    results = []

    print("=" * 60)
    print("HW-CI PIPELINE")
    print("=" * 60)

    print(f"\nDesign: {design.describe()}")
    print(f"Branch: {branch}")
    print(f"Commit: {commit_hash}")

    work_dir = Path("results") / design.name

    print("\n[1/4] Running lint...")
    lint_result = run_lint(
        design.rtl_files,
        top_module=design.top,
        include_dirs=design.include_dirs,
        defines=design.defines,
    )
    results.append(lint_result)
    print(
        f"       {lint_result['status']} "
        f"({lint_result['runtime_sec']} sec)"
    )

    if lint_result["returncode"] != 0:
        print_failure_output(lint_result)
        print("\nPipeline stopped: lint failed.")

    else:
        print("\n[2/4] Running synthesis...")
        synth_result = run_synthesis(
            design.rtl_files,
            design.top,
            output_dir=work_dir / "synthesis",
            include_dirs=design.include_dirs,
            defines=design.defines,
        )
        results.append(synth_result)
        print(
            f"       {synth_result['status']} "
            f"({synth_result['runtime_sec']} sec)"
        )

        if synth_result["returncode"] != 0:
            print_failure_output(synth_result)
            print("\nPipeline stopped: synthesis failed.")

        else:
            sim_ok = True

            if design.tb_file is None:
                print(
                    "\n[3/4] Simulation skipped: no testbench found. "
                    "Pass --tb or set sim.testbench in hwci.toml."
                )
            else:
                print("\n[3/4] Running simulation...")
                sim_result = run_simulation(
                    design.rtl_files,
                    design.tb_file,
                    build_dir=work_dir / "simulation",
                    include_dirs=design.include_dirs,
                    defines=design.defines,
                    tb_top=design.tb_top,
                    pass_regex=design.sim_pass_regex,
                    fail_regex=design.sim_fail_regex,
                )
                results.append(sim_result)
                print(
                    f"       {sim_result['status']} "
                    f"({sim_result['runtime_sec']} sec)"
                )

                if sim_result["status"] != "PASS":
                    sim_ok = False
                    print_failure_output(sim_result)
                    print("\nPipeline stopped: simulation failed.")

            if sim_ok:
                run_sta_stage(design, results)

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
        design.name,
    )

    for result in results:
        if result["stage"] == "sta":
            corner = result["corner"]
            previous = get_previous_corner_timing(build_id, corner, design.name)

            if previous is not None:
                previous_setup, previous_hold = previous

                if None not in (
                    result["setup_wns"],
                    result["hold_whs"],
                    previous_setup,
                    previous_hold,
                ):
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


def run_pipeline(rtl_file, tb_file, top_module, repo_path):
    """Original entry point: one RTL file, explicit testbench and top."""
    return run_design_pipeline(
        legacy_design(rtl_file, tb_file, top_module, repo_path)
    )


USAGE = """\
Usage:
  python flow/pipeline.py <repo_path> [--top T] [--rtl F [F ...]] [--tb F]
                                      [--name N] [--sta {auto,require,skip}]
  python flow/pipeline.py <rtl_file> <testbench_file> <top_module> <repo_path>

With only <repo_path>, the RTL files, top module and testbench come from
<repo_path>/hwci.toml if present, otherwise they are discovered.
Relative --rtl / --tb paths are resolved against <repo_path>.
"""


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python flow/pipeline.py",
        usage="%(prog)s <repo_path> [options]   (or the 4-argument form below)",
        description="Run lint, synthesis, simulation and STA on any RTL repository.",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo_path")
    parser.add_argument("--top")
    parser.add_argument("--rtl", nargs="+")
    parser.add_argument("--tb")
    parser.add_argument("--name")
    parser.add_argument("--sta", choices=("auto", "require", "skip"))
    return parser.parse_args(argv)


def main(argv):
    # Original form: <rtl> <tb> <top> <repo>
    if len(argv) == 4 and not any(arg.startswith("-") for arg in argv):
        design = legacy_design(*argv)
    else:
        args = parse_args(argv)
        try:
            design = resolve_design(
                args.repo_path,
                top=args.top,
                rtl=args.rtl,
                tb=args.tb,
                name=args.name,
                sta_mode=args.sta,
            )
        except DesignError as exc:
            print(f"Cannot determine the design: {exc}", file=sys.stderr)
            return 2

    _, overall_status = run_design_pipeline(design)
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
