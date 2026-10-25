from pathlib import Path

import pytest

from design_config import DesignError, legacy_design, resolve_design

FIXTURE = Path(__file__).parent / "fixtures" / "adder"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_discovers_adder_without_any_configuration():
    design = resolve_design(FIXTURE)

    assert design.name == "adder"
    assert design.top == "adder"
    assert {f.name for f in design.rtl_files} == {"adder.v", "full_adder.v"}
    assert design.tb_file.name == "adder_tb.v"
    assert design.sta_mode == "auto"


def test_testbench_is_never_treated_as_rtl():
    design = resolve_design(FIXTURE)

    assert design.tb_file not in design.rtl_files


def test_src_directory_wins_over_a_copy_in_the_repo_root(tmp_path):
    module = "module core(input a, output y); assign y = a; endmodule\n"
    write(tmp_path / "core.v", module)
    write(tmp_path / "src" / "core.v", module)

    design = resolve_design(tmp_path)

    assert [f.relative_to(tmp_path) for f in design.rtl_files] == [Path("src/core.v")]


def test_generated_output_directories_are_ignored(tmp_path):
    write(tmp_path / "core.v", "module core(input a, output y); assign y = a; endmodule\n")
    write(tmp_path / "results" / "routing" / "core.nl.v", "module core_netlist(); endmodule\n")

    design = resolve_design(tmp_path)

    assert [f.name for f in design.rtl_files] == ["core.v"]


def test_ambiguous_top_asks_for_an_explicit_choice(tmp_path):
    write(tmp_path / "a.v", "module alpha(input x, output y); assign y = x; endmodule\n")
    write(tmp_path / "b.v", "module beta(input x, output y); assign y = ~x; endmodule\n")

    with pytest.raises(DesignError, match="alpha, beta"):
        resolve_design(tmp_path)

    assert resolve_design(tmp_path, top="beta").top == "beta"


def test_unknown_top_is_rejected(tmp_path):
    write(tmp_path / "a.v", "module alpha(input x, output y); assign y = x; endmodule\n")

    with pytest.raises(DesignError, match="not declared"):
        resolve_design(tmp_path, top="nope")


def test_repository_without_rtl_is_rejected(tmp_path):
    with pytest.raises(DesignError, match="No RTL"):
        resolve_design(tmp_path)


def test_manifest_overrides_discovery(tmp_path):
    write(tmp_path / "hw" / "alu.v", "module alu(input a, output y); assign y = a; endmodule\n")
    write(tmp_path / "hw" / "other.v", "module other(input a, output y); assign y = a; endmodule\n")
    write(tmp_path / "verif" / "alu_check.v", "module alu_check; initial $finish; endmodule\n")
    write(
        tmp_path / "hwci.toml",
        """
name = "my_alu"
top = "alu"
rtl = ["hw/alu.v"]
defines = ["WIDTH=8"]

[sim]
testbench = "verif/alu_check.v"
top = "alu_check"
pass_regex = "ALL GOOD"

[sta]
mode = "skip"
""",
    )

    design = resolve_design(tmp_path)

    assert design.name == "my_alu"
    assert design.top == "alu"
    assert [f.name for f in design.rtl_files] == ["alu.v"]
    assert design.tb_file == tmp_path / "verif" / "alu_check.v"
    assert design.tb_top == "alu_check"
    assert design.sim_pass_regex == "ALL GOOD"
    assert design.defines == ["WIDTH=8"]
    assert design.sta_mode == "skip"


def test_explicit_arguments_beat_the_manifest(tmp_path):
    write(tmp_path / "a.v", "module alpha(input x, output y); assign y = x; endmodule\n")
    write(tmp_path / "b.v", "module beta(input x, output y); assign y = x; endmodule\n")
    write(tmp_path / "hwci.toml", 'top = "alpha"\n')

    assert resolve_design(tmp_path, top="beta").top == "beta"


def test_manifest_glob_that_matches_nothing_is_an_error(tmp_path):
    write(tmp_path / "hwci.toml", 'rtl = ["missing/*.v"]\n')

    with pytest.raises(DesignError, match="missing"):
        resolve_design(tmp_path)


def test_invalid_sta_mode_is_rejected():
    with pytest.raises(DesignError, match="STA mode"):
        resolve_design(FIXTURE, sta_mode="sometimes")


def test_missing_testbench_is_allowed_but_reported_as_none(tmp_path):
    write(tmp_path / "core.v", "module core(input a, output y); assign y = a; endmodule\n")

    assert resolve_design(tmp_path).tb_file is None


def test_legacy_form_keeps_openlane_paths_and_requires_sta(tmp_path):
    design = legacy_design("x/async_fifo.v", "x/async_fifo_tb.v", "async_fifo", tmp_path)

    assert design.sta_mode == "require"
    assert design.sta_netlist == tmp_path / "results" / "routing" / "async_fifo.nl.v"
    assert design.sta_sdc == tmp_path / "src" / "async_fifo.sdc"
    assert design.sta_spef == (
        tmp_path / "results" / "routing" / "mca" / "spef" / "async_fifo.nom.spef"
    )
