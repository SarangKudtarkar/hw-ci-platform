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

PDK_ROOT = Path(
    os.environ.get("PDK_ROOT", "/home/sarang/.volare")
)

DEFAULT_LIBERTY = (
    PDK_ROOT
    / "sky130A/libs.ref/sky130_fd_sc_hd/lib/"
    / "sky130_fd_sc_hd__tt_025C_1v80.lib"
)


def run_sta(
    netlist,
    sdc,
    spef,
    top_module,
    liberty=DEFAULT_LIBERTY,
    output_dir="results/sta",
):
    netlist = Path(netlist).resolve()
    sdc = Path(sdc).resolve()
    spef = Path(spef).resolve()
    liberty = Path(liberty).resolve()
    output_dir = (PROJECT_ROOT / output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    tcl_file = output_dir / "sta.tcl"
    report_file = output_dir / "sta_report.txt"

    for path in (netlist, sdc, spef, liberty):
        if not path.exists():
            raise FileNotFoundError(f"STA input not found: {path}")

    tcl = f"""read_liberty {liberty}
read_verilog {netlist}
link_design {top_module}
read_sdc {sdc}
read_spef {spef}

report_checks -path_delay max -group_count 10
report_checks -path_delay min -group_count 10

report_worst_slack -max
report_worst_slack -min

exit
"""

    tcl_file.write_text(tcl)

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

    setup_wns = (
        float(worst_slacks[0])
        if len(worst_slacks) >= 1
        else None
    )

    hold_whs = (
        float(worst_slacks[1])
        if len(worst_slacks) >= 2
        else None
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
        "stage": "sta",
        "status": status,
        "runtime_sec": round(runtime, 3),
        "returncode": result.returncode,
        "setup_wns": setup_wns,
        "hold_whs": hold_whs,
        "report": str(report_file),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 5:
        print(
            "Usage: python flow/sta.py "
            "<netlist> <sdc> <spef> <top_module>"
        )
        sys.exit(2)

    result = run_sta(
        netlist=sys.argv[1],
        sdc=sys.argv[2],
        spef=sys.argv[3],
        top_module=sys.argv[4],
    )

    print(f"Stage:      {result['stage']}")
    print(f"Status:     {result['status']}")
    print(f"Runtime:    {result['runtime_sec']} sec")
    print(f"Setup WNS:  {result['setup_wns']} ns")
    print(f"Hold WHS:   {result['hold_whs']} ns")
    print(f"Report:     {result['report']}")

    sys.exit(0 if result["status"] == "PASS" else 1)
