import stat
from pathlib import Path

from tests.toolchains import tool_works


def install_tool(directory: Path, name: str, exit_code: int) -> None:
    script = directory / name
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


def test_a_tool_that_reports_its_version_works(monkeypatch, tmp_path):
    install_tool(tmp_path, "faketool", 0)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert tool_works("faketool")


def test_a_stub_that_fails_its_version_does_not_work(monkeypatch, tmp_path):
    """rustup's `rustfmt` stub is on PATH even when the component is not installed."""
    install_tool(tmp_path, "faketool", 1)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert not tool_works("faketool")


def test_a_tool_that_is_not_on_path_does_not_work(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert not tool_works("faketool")
