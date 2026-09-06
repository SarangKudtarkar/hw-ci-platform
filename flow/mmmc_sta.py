import os
import re
import subprocess
import time
from pathlib import Path


OPENLANE_IMAGE = (
    "efabless/openlane:"
    "e73fb3c57e687a0023fcd4dcfd1566ecd478362a-amd64"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDK_ROOT = Path(os.environ.get("PDK_ROOT", str(Path.home() / ".volare")))

LIB_DIR = (
    PDK_ROOT
    / "sky130A/libs.ref/sky130_fd_sc_hd/lib"
)

CORNERS = {
    "ss_100C_1v60": LIB_DIR / "sky130_fd_sc_hd__ss_100C_1v60.lib",
    "tt_025C_1v80": LIB_DIR / "sky130_fd_sc_hd__tt_025C_1v80.lib",
    "ff_n40C_1v76": LIB_DIR / "sky130_fd_sc_hd__ff_n40C_1v76.lib",
}


def run_corner(netlist, sdc, spef, top_module, corner, liberty):
    output_dir = PROJECT_ROOT / "results" / "mmmc_sta"
    output_dir.mkdir(parents=True, exist_ok=True)

    tcl_file = output_dir / f"{corner}.tcl"
    report_file = output_dir / f"{corner}_report.txt"

    tcl_file.write_text(
        f"""read_liberty {liberty}
read_verilog {Path(netlist).resolve()}
link_design {top_module}
read_sdc {Path(sdc).resolve()}
read_spef {Path(spef).resolve()}

report_checks -path_delay max -group_count 100
report_checks -path_delay min -group_count 100

report_worst_slack -max
report_worst_slack -min

exit
"""
    )

    uid = os.getuid()
    gid = os.getgid()

    start = time.time()

    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{PROJECT_ROOT.parent}:{PROJECT_ROOT.parent}",
        "-v",
        f"{PDK_ROOT}:{PDK_ROOT}",
        "--user",
        f"{uid}:{gid}",
        OPENLANE_IMAGE,
        "sta",
        str(tcl_file),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    runtime = time.time() - start

    output = result.stdout + "\n" + result.stderr
    report_file.write_text(output)

    worst_slacks = re.findall(
        r"worst slack\s+(-?\d+(?:\.\d+)?)",
        output,
        re.IGNORECASE,
    )

    setup_wns = float(worst_slacks[0]) if len(worst_slacks) >= 1 else None
    hold_whs = float(worst_slacks[1]) if len(worst_slacks) >= 2 else None

    path_slacks = [
        float(value)
        for value in re.findall(
            r"(-?\d+(?:\.\d+)?)\\s+slack\\s+\\((?:MET|VIOLATED)\\)",
            output,
            re.IGNORECASE,
        )
    ]

    setup_tns = sum(
        slack for slack in path_slacks[:100]
        if slack < 0
    )

    hold_tns = sum(
        slack for slack in path_slacks[100:200]
        if slack < 0
    )

    status = (
        "PASS"
        if result.returncode == 0
        and setup_wns is not None
        and hold_whs is not None
        and setup_wns >= 0
        and hold_whs >= 0
        else "FAIL"
    )

    return {
        "corner": corner,
        "status": status,
        "runtime_sec": round(runtime, 3),
        "setup_wns": setup_wns,
        "hold_whs": hold_whs,
        "setup_tns": round(setup_tns, 3),
        "hold_tns": round(hold_tns, 3),
        "report": str(report_file),
    }


def run_mmmc_sta(netlist, sdc, spef, top_module):
    print("=" * 60)
    print("MMMC STA")
    print("=" * 60)

    results = []

    for corner, liberty in CORNERS.items():
        print(f"\n[{corner}]")

        if not liberty.exists():
            print(f"Liberty not found: {liberty}")
            results.append({
                "corner": corner,
                "status": "FAIL",
                "runtime_sec": 0,
                "setup_wns": None,
                "hold_whs": None,
            })
            continue

        result = run_corner(
            netlist,
            sdc,
            spef,
            top_module,
            corner,
            liberty,
        )

        results.append(result)

        print(f"Status:     {result['status']}")
        print(f"Setup WNS:  {result['setup_wns']} ns")
        print(f"Hold WHS:   {result['hold_whs']} ns")
        print(f"Runtime:    {result['runtime_sec']} sec")

    overall = (
        "PASS"
        if results and all(r["status"] == "PASS" for r in results)
        else "FAIL"
    )

    print("\n" + "=" * 60)
    print(f"MMMC RESULT: {overall}")
    print("=" * 60)

    return results, overall


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 5:
        print(
            f"Usage: python {sys.argv[0]} "
            "<netlist> <sdc> <spef> <top_module>"
        )
        sys.exit(2)

    _, overall = run_mmmc_sta(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
    )

    sys.exit(0 if overall == "PASS" else 1)
