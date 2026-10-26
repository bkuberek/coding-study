import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from coding_study.entrypoints import launcher
from coding_study.entrypoints.shared import ExitCode

PYPROJECT = Path(__file__).resolve().parents[3] / "pyproject.toml"
"""The installable project at the repository root defines the `cstudy` script."""


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
