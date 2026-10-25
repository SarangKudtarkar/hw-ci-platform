import shutil
import sqlite3
from pathlib import Path

import pytest

import pipeline
import simulate
from db import database
from design_config import resolve_design
from lint import run_lint
from simulate import run_simulation
from synth import run_synthesis

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "adder"

needs_eda = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("verilator", "yosys", "iverilog")),
    reason="verilator, yosys and iverilog are required",
)


@pytest.fixture
def adder(tmp_path):
    """A private copy of the adder that a test may modify."""
    target = tmp_path / "adder"
    shutil.copytree(FIXTURE, target)
    return target


@pytest.fixture
def break_adder(adder):
    """Make the adder wrong while keeping it lint- and synthesis-clean."""
    full_adder = adder / "src" / "full_adder.v"
    full_adder.write_text(
        full_adder.read_text().replace(
            "(a & b) | (a & cin) | (b & cin)", "(a & b) | (a | cin)"
        )
    )
    return adder


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.chdir(tmp_path)
    return tmp_path / "test.db"


# --------------------------------------------------------------------------
# Simulation verdict (no EDA tools needed)
# --------------------------------------------------------------------------

def test_nonzero_exit_code_fails():
    assert simulate.judge(1, "")[0] == "FAIL"


def test_failure_marker_fails_even_when_the_simulator_exits_zero():
    status, detail = simulate.judge(0, "ERROR: expected 3, got 4\nTEST FINISHED")

    assert status == "FAIL"
    assert "expected 3" in detail


def test_lower_case_words_do_not_trip_the_failure_marker():
    assert simulate.judge(0, "errors: 0\nno failures\n")[0] == "PASS"


def test_configured_pass_marker_is_required():
    assert simulate.judge(0, "done", pass_regex="TEST PASSED")[0] == "FAIL"
    assert simulate.judge(0, "TEST PASSED", pass_regex="TEST PASSED")[0] == "PASS"


# --------------------------------------------------------------------------
# Stages on the adder
# --------------------------------------------------------------------------

@needs_eda
def test_stages_accept_a_multi_file_design(tmp_path):
    design = resolve_design(FIXTURE)

    lint = run_lint(design.rtl_files, top_module=design.top)
    synth = run_synthesis(design.rtl_files, design.top, output_dir=tmp_path / "synth")
    sim = run_simulation(design.rtl_files, design.tb_file, build_dir=tmp_path / "sim")

    assert lint["status"] == "PASS", lint["stderr"]
    assert synth["status"] == "PASS", synth["stderr"]
    assert sim["status"] == "PASS", sim["stdout"]
    assert (tmp_path / "synth" / "adder_netlist.v").exists()


@needs_eda
def test_single_path_argument_still_works(tmp_path):
    rtl = tmp_path / "inv.v"
    rtl.write_text("module inv(input a, output y); assign y = ~a; endmodule\n")

    assert run_lint(rtl)["status"] == "PASS"
    assert run_synthesis(rtl, "inv", output_dir=tmp_path / "out")["status"] == "PASS"


@needs_eda
def test_synthesis_fails_when_a_submodule_is_missing(adder, tmp_path):
    result = run_synthesis(adder / "src" / "adder.v", "adder", output_dir=tmp_path / "out")

    assert result["status"] == "FAIL"


@needs_eda
def test_wrong_design_fails_simulation_although_the_testbench_exits_zero(break_adder, tmp_path):
    design = resolve_design(break_adder)

    sim = run_simulation(design.rtl_files, design.tb_file, build_dir=tmp_path / "sim")

    assert sim["status"] == "FAIL"
    assert "TEST FAILED" in sim["stdout"]
    assert sim["returncode"] != 0


# --------------------------------------------------------------------------
# Whole pipeline
# --------------------------------------------------------------------------

@needs_eda
def test_pipeline_runs_on_an_adder_from_just_its_folder(adder, temp_db):
    code = pipeline.main([str(adder)])

    assert code == 0

    with sqlite3.connect(temp_db) as conn:
        build = conn.execute("SELECT id, status, design FROM builds").fetchone()
        stages = conn.execute(
            "SELECT stage, status FROM stage_results WHERE build_id = ?", (build[0],)
        ).fetchall()

    assert build[1:] == ("PASS", "adder")
    # STA is skipped for a design that has no routed netlist.
    assert stages == [("lint", "PASS"), ("synthesis", "PASS"), ("simulation", "PASS")]


@needs_eda
def test_pipeline_fails_a_wrong_design(break_adder, temp_db):
    assert pipeline.main([str(break_adder)]) == 1

    with sqlite3.connect(temp_db) as conn:
        assert conn.execute("SELECT status FROM builds").fetchone() == ("FAIL",)


@needs_eda
def test_pipeline_accepts_explicit_arguments(adder, temp_db):
    code = pipeline.main(
        [
            str(adder),
            "--top", "adder",
            "--rtl", "src/adder.v", "src/full_adder.v",
            "--tb", "tb/adder_tb.v",
            "--name", "adder4",
        ]
    )

    assert code == 0

    with sqlite3.connect(temp_db) as conn:
        assert conn.execute("SELECT design FROM builds").fetchone() == ("adder4",)


@needs_eda
def test_original_four_argument_form_still_works(adder, temp_db, monkeypatch):
    calls = []

    def fake_sta(netlist, sdc, spef, top_module, output_dir=None):
        calls.append((netlist.name, sdc.name, spef.name, top_module))
        return [], "PASS"

    monkeypatch.setattr(pipeline, "run_mmmc_sta", fake_sta)

    single_file = adder / "adder_single.v"
    single_file.write_text(
        (adder / "src" / "adder.v").read_text()
        + (adder / "src" / "full_adder.v").read_text()
    )

    code = pipeline.main(
        [str(single_file), str(adder / "tb" / "adder_tb.v"), "adder", str(adder)]
    )

    assert code == 0
    # The original form always runs STA, with the OpenLane default paths.
    assert calls == [("adder.nl.v", "adder.sdc", "adder.nom.spef", "adder")]


def test_pipeline_reports_an_undeterminable_design(tmp_path, capsys):
    assert pipeline.main([str(tmp_path)]) == 2
    assert "Cannot determine the design" in capsys.readouterr().err


# --------------------------------------------------------------------------
# STA stage selection
# --------------------------------------------------------------------------

def run_sta_stage_with(design, monkeypatch):
    calls = []

    def fake_sta(**kwargs):
        calls.append(kwargs)
        return [], "PASS"

    monkeypatch.setattr(pipeline, "run_mmmc_sta", fake_sta)
    pipeline.run_sta_stage(design, [])
    return calls


def test_sta_is_skipped_in_auto_mode_without_routed_inputs(monkeypatch):
    design = resolve_design(FIXTURE)

    assert run_sta_stage_with(design, monkeypatch) == []


def test_sta_is_skipped_in_skip_mode_even_if_inputs_exist(adder, monkeypatch):
    for path in ("results/routing/adder.nl.v", "src/adder.sdc", "results/routing/mca/spef/adder.nom.spef"):
        target = adder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("")

    design = resolve_design(adder, sta_mode="skip")

    assert run_sta_stage_with(design, monkeypatch) == []


def test_sta_runs_in_auto_mode_when_inputs_exist(adder, monkeypatch):
    for path in ("results/routing/adder.nl.v", "src/adder.sdc", "results/routing/mca/spef/adder.nom.spef"):
        target = adder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("")

    calls = run_sta_stage_with(resolve_design(adder), monkeypatch)

    assert len(calls) == 1
    assert calls[0]["top_module"] == "adder"


def test_sta_runs_in_require_mode_and_reports_missing_inputs(monkeypatch, capsys):
    design = resolve_design(FIXTURE, sta_mode="require")

    calls = run_sta_stage_with(design, monkeypatch)

    assert len(calls) == 1
    assert "missing STA input" in capsys.readouterr().out


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

def test_existing_database_is_upgraded_and_history_is_attributed_to_the_fifo(tmp_path, monkeypatch):
    old = tmp_path / "old.db"
    shutil.copy(ROOT / "db" / "build.db", old)
    monkeypatch.setattr(database, "DB_PATH", old)

    with database.connect() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(builds)")]
        designs = {row[0] for row in conn.execute("SELECT design FROM builds")}
        build_count = conn.execute("SELECT COUNT(*) FROM builds").fetchone()[0]

    assert "design" in columns
    assert designs == {database.LEGACY_DESIGN}
    assert build_count > 0


def test_fresh_database_gets_the_current_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "fresh.db")

    with database.connect() as conn:
        builds = [row[1] for row in conn.execute("PRAGMA table_info(builds)")]
        timing = [row[1] for row in conn.execute("PRAGMA table_info(timing_results)")]

    assert "design" in builds
    assert "corner" in timing


def test_timing_regression_is_never_compared_across_designs(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "t.db")

    fifo_build = database.create_build("c1", "main", "t", "PASS", 1.0, "async_fifo")
    database.create_timing_result(fifo_build, "tt", 3.0, 0.3)
    adder_build = database.create_build("c2", "main", "t", "PASS", 1.0, "adder")
    database.create_timing_result(adder_build, "tt", 9.0, 0.9)
    next_adder = database.create_build("c3", "main", "t", "PASS", 1.0, "adder")
    next_fifo = database.create_build("c4", "main", "t", "PASS", 1.0, "async_fifo")

    assert database.get_previous_corner_timing(next_adder, "tt", "adder") == (9.0, 0.9)
    assert database.get_previous_corner_timing(next_fifo, "tt", "async_fifo") == (3.0, 0.3)
    assert database.get_previous_corner_timing(next_adder, "tt", "other") is None
