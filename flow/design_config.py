"""Describe the design under test: which files to lint, synthesise and simulate.

A design comes from one of three places, in order of precedence:

1. explicit arguments (CLI flags / function arguments)
2. an ``hwci.toml`` manifest in the root of the IP repository
3. auto-discovery (RTL files, top module and testbench are inferred)

Nothing in here is specific to any particular IP.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_NAME = "hwci.toml"

RTL_SUFFIXES = {".v", ".sv"}

# Directories searched first for RTL, in this order. The first one that
# contains RTL wins; otherwise the repository root, then the whole tree.
PREFERRED_RTL_DIRS = ("src", "rtl", "hdl", "design")

# Directories that hold generated output, never source.
IGNORED_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    "results", "logs", "reports", "runs", "build", "obj_dir",
}

TB_NAME_PATTERN = re.compile(
    r"(^|_)(tb|test|testbench)(_|$)|testbench", re.IGNORECASE
)

# Testbenches usually print a marker and call $finish, which exits 0 even when
# a check failed, so the exit code alone cannot be trusted. Upper-case words
# only, so lines such as "errors: 0" do not trip it.
DEFAULT_SIM_FAIL_REGEX = r"\b(ERROR|FAIL|FAILED|MISMATCH)\b"

STA_MODES = ("auto", "require", "skip")


class DesignError(Exception):
    """The design could not be determined or the manifest is invalid."""


@dataclass
class Design:
    name: str
    top: str
    repo_path: Path
    rtl_files: list[Path]
    tb_file: Path | None = None
    tb_top: str | None = None
    include_dirs: list[Path] = field(default_factory=list)
    defines: list[str] = field(default_factory=list)
    sim_pass_regex: str | None = None
    sim_fail_regex: str = DEFAULT_SIM_FAIL_REGEX
    sta_mode: str = "auto"
    sta_netlist: Path | None = None
    sta_sdc: Path | None = None
    sta_spef: Path | None = None

    def __post_init__(self):
        # Defaults follow the OpenLane output layout of the input repository.
        routing = self.repo_path / "results" / "routing"
        if self.sta_netlist is None:
            self.sta_netlist = routing / f"{self.top}.nl.v"
        if self.sta_sdc is None:
            self.sta_sdc = self.repo_path / "src" / f"{self.top}.sdc"
        if self.sta_spef is None:
            self.sta_spef = routing / "mca" / "spef" / f"{self.top}.nom.spef"

    def missing_sta_inputs(self) -> list[Path]:
        return [
            p for p in (self.sta_netlist, self.sta_sdc, self.sta_spef)
            if not p.exists()
        ]

    def describe(self) -> str:
        tb = self.tb_file.name if self.tb_file else "none"
        return (
            f"{self.name} (top={self.top}, "
            f"{len(self.rtl_files)} RTL file(s), testbench={tb})"
        )


def legacy_design(rtl_file, tb_file, top_module, repo_path) -> Design:
    """The original four-argument form: one RTL file, STA required."""
    repo_path = Path(repo_path).resolve()
    return Design(
        name=top_module,
        top=top_module,
        repo_path=repo_path,
        rtl_files=[Path(rtl_file)],
        tb_file=Path(tb_file),
        sta_mode="require",
    )


# --------------------------------------------------------------------------
# Verilog scanning
# --------------------------------------------------------------------------

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_MODULE_DECL = re.compile(r"\bmodule\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)")


def _strip_comments(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def _read(path: Path) -> str:
    return _strip_comments(path.read_text(errors="replace"))


def declared_modules(path: Path) -> list[str]:
    return _MODULE_DECL.findall(_read(path))


def find_top_candidates(rtl_files: list[Path]) -> list[str]:
    """Modules that are declared but never instantiated by another module."""
    texts = [_read(p) for p in rtl_files]
    declared = [m for t in texts for m in _MODULE_DECL.findall(t)]
    body = "\n".join(_MODULE_DECL.sub("module", t) for t in texts)

    instantiated = set()
    for name in set(declared):
        # "name inst (", "name #(...) inst (", "name inst [3:0] ("
        if re.search(rf"\b{re.escape(name)}\s*#", body) or re.search(
            rf"\b{re.escape(name)}\s+[A-Za-z_]\w*\s*[\(\[]", body
        ):
            instantiated.add(name)

    seen, tops = set(), []
    for name in declared:
        if name not in instantiated and name not in seen:
            seen.add(name)
            tops.append(name)
    return tops


def _walk(root: Path, recursive: bool = True):
    for path in sorted(root.iterdir()):
        if path.name in IGNORED_DIRS or path.name.startswith("."):
            continue
        if path.is_dir():
            if recursive:
                yield from _walk(path)
        else:
            yield path


def is_testbench_file(path: Path) -> bool:
    if path.suffix not in RTL_SUFFIXES:
        return False
    if TB_NAME_PATTERN.search(path.stem):
        return True
    text = _read(path)
    return bool(re.search(r"\$(finish|stop)\b", text)) and not re.search(
        r"\b(always_ff|always_comb)\b", text
    )


def discover_rtl_files(repo_path: Path) -> list[Path]:
    def rtl_in(files):
        return [
            f for f in files
            if f.suffix in RTL_SUFFIXES and not is_testbench_file(f)
        ]

    for dirname in PREFERRED_RTL_DIRS:
        folder = repo_path / dirname
        if folder.is_dir():
            found = rtl_in(_walk(folder))
            if found:
                return found

    found = rtl_in(_walk(repo_path, recursive=False))
    if found:
        return found

    return rtl_in(_walk(repo_path))


def discover_testbench(repo_path: Path, top: str) -> Path | None:
    candidates = [
        f for f in _walk(repo_path) if is_testbench_file(f)
    ]
    if not candidates:
        return None

    # Prefer a testbench named after the top module, e.g. adder_tb.v / tb_adder.v
    named = [f for f in candidates if top.lower() in f.stem.lower()]
    pool = named or candidates
    if len(pool) > 1:
        # Shallowest path first, then alphabetical, so the choice is stable.
        pool = sorted(pool, key=lambda f: (len(f.parts), str(f)))
    return pool[0]


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------

def _expand(repo_path: Path, patterns) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        matches = sorted(repo_path.glob(pattern))
        if not matches:
            raise DesignError(f"No file matches '{pattern}' in {repo_path}")
        files.extend(m for m in matches if m.is_file())
    return files


def _load_manifest(repo_path: Path) -> dict:
    manifest_path = repo_path / MANIFEST_NAME
    if not manifest_path.exists():
        return {}
    try:
        return tomllib.loads(manifest_path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise DesignError(f"Invalid {manifest_path}: {exc}") from exc


def _rel(repo_path: Path, value) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_path / path


def resolve_design(
    repo_path,
    top: str | None = None,
    rtl: list[str] | None = None,
    tb: str | None = None,
    name: str | None = None,
    sta_mode: str | None = None,
) -> Design:
    """Build a Design for ``repo_path`` from arguments, manifest and discovery."""
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise DesignError(f"Repository path is not a directory: {repo_path}")

    manifest = _load_manifest(repo_path)
    sim_cfg = manifest.get("sim", {})
    sta_cfg = manifest.get("sta", {})

    # ---- RTL files
    if rtl:
        rtl_files = [_rel(repo_path, r) for r in rtl]
    elif manifest.get("rtl"):
        rtl_files = _expand(repo_path, manifest["rtl"])
    else:
        rtl_files = discover_rtl_files(repo_path)
    if not rtl_files:
        raise DesignError(
            f"No RTL (.v/.sv) files found in {repo_path}. "
            f"Pass --rtl or add an {MANIFEST_NAME}."
        )
    for f in rtl_files:
        if not f.is_file():
            raise DesignError(f"RTL file not found: {f}")

    # ---- top module
    top = top or manifest.get("top")
    if not top:
        candidates = find_top_candidates(rtl_files)
        if len(candidates) == 1:
            top = candidates[0]
        elif not candidates:
            raise DesignError(
                "Could not find a top module (every module is instantiated "
                "by another). Pass --top."
            )
        else:
            raise DesignError(
                "Several possible top modules: "
                + ", ".join(candidates)
                + ". Pass --top or set 'top' in "
                + MANIFEST_NAME
                + "."
            )
    else:
        known = {m for f in rtl_files for m in declared_modules(f)}
        if known and top not in known:
            raise DesignError(
                f"Top module '{top}' is not declared in the RTL files "
                f"(found: {', '.join(sorted(known))})."
            )

    # ---- testbench
    tb_value = tb or sim_cfg.get("testbench")
    if tb_value:
        tb_file = _rel(repo_path, tb_value)
        if not tb_file.is_file():
            raise DesignError(f"Testbench not found: {tb_file}")
    else:
        tb_file = discover_testbench(repo_path, top)
        if tb_file in rtl_files:
            tb_file = None

    # ---- STA
    mode = sta_mode or sta_cfg.get("mode", "auto")
    if mode not in STA_MODES:
        raise DesignError(f"STA mode must be one of {STA_MODES}, got '{mode}'")

    def sta_path(key):
        return _rel(repo_path, sta_cfg[key]) if sta_cfg.get(key) else None

    return Design(
        name=name or manifest.get("name") or top,
        top=top,
        repo_path=repo_path,
        rtl_files=rtl_files,
        tb_file=tb_file,
        tb_top=sim_cfg.get("top"),
        include_dirs=[_rel(repo_path, d) for d in manifest.get("include_dirs", [])],
        defines=list(manifest.get("defines", [])),
        sim_pass_regex=sim_cfg.get("pass_regex"),
        sim_fail_regex=sim_cfg.get("fail_regex", DEFAULT_SIM_FAIL_REGEX),
        sta_mode=mode,
        sta_netlist=sta_path("netlist"),
        sta_sdc=sta_path("sdc"),
        sta_spef=sta_path("spef"),
    )
