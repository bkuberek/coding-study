import os
import subprocess
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import pytest

from coding_study.entrypoints import launcher
from coding_study.entrypoints.shared import ExitCode

PYPROJECT = Path(__file__).resolve().parents[3] / "pyproject.toml"
"""The installable project at the repository root defines the `cstudy` script."""
INTERRUPTED_INSIDE_AN_EXEC = """from coding_study.entrypoints import launcher


def interrupted(_name):
    exec("raise KeyboardInterrupt", {})


launcher.import_module = interrupted
"""
"""A `sitecustomize` whose Ctrl-C leaves an `exec` while the CLI imports, as one does when it lands
while a dataclass makes its methods."""


def test_the_cs_script_starts_through_the_launcher():
    scripts = tomllib.loads(PYPROJECT.read_text())["project"]["scripts"]
    assert scripts["cstudy"] == "coding_study.entrypoints.launcher:main"


def test_runs_the_cli(monkeypatch):
    ran: list[str] = []
    cli = SimpleNamespace(main=lambda: ran.append("cli"))
    monkeypatch.setattr(launcher, "import_module", lambda _name: cli)
    launcher.main()
    assert ran == ["cli"]


def test_imports_the_cli_module(monkeypatch):
    imported: list[str] = []

    def record(name: str) -> SimpleNamespace:
        imported.append(name)
        return SimpleNamespace(main=lambda: None)

    monkeypatch.setattr(launcher, "import_module", record)
    launcher.main()
    assert imported == ["coding_study.entrypoints.cli"]


def test_ctrl_c_while_the_cli_imports_exits_130(monkeypatch):
    def interrupted(_name: str) -> SimpleNamespace:
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher, "import_module", interrupted)
    with pytest.raises(SystemExit) as exited:
        launcher.main()
    assert exited.value.code == ExitCode.INTERRUPTED


def test_python_dash_m_coding_study_runs_the_cli():
    """`cstudy serve` starts its runs as `sys.executable -m coding_study`, the same install."""
    finished = subprocess.run(
        [sys.executable, "-m", "coding_study", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finished.stdout == f"cstudy {version('coding-study')}\n"


def test_ctrl_c_inside_an_exec_exits_130_under_python_dash_m(tmp_path):
    """A run of `cstudy serve` that Cancel stops while it starts ends 130, not by SIGINT."""
    (tmp_path / "sitecustomize.py").write_text(INTERRUPTED_INSIDE_AN_EXEC)
    search_path = os.pathsep.join(filter(None, (str(tmp_path), os.environ.get("PYTHONPATH"))))
    finished = subprocess.run(
        [sys.executable, "-m", "coding_study", "--version"],
        env={**os.environ, "PYTHONPATH": search_path},
        capture_output=True,
        check=False,
    )
    assert finished.returncode == ExitCode.INTERRUPTED
