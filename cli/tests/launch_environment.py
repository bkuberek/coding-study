"""What a process `cstudy` starts for user code, or a tool on it, inherits
(docs/specs/runners.md#process-environment): the secrets a shell holds do not reach it, and what
a toolchain needs does."""

import os
import stat
from collections.abc import Iterable
from pathlib import Path

import pytest

SECRETS = {
    "CSTUDY_TEST_SECRET_TOKEN": "cstudy-test-secret-token-value",
    "AWS_SECRET_ACCESS_KEY": "aws-secret-access-key-value",
}
"""Set in the environment of the process that starts the launch under test."""
NEEDED = ("PATH", "HOME")
"""Set in that environment, and passed on."""


def plant_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """The environment of a shell that holds `SECRETS`, and a home directory."""
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("HOME", os.environ.get("HOME", "/home/cstudy-test"))


def environment_recorder(record: Path) -> str:
    """Python source that writes the names and values of its own environment to `record`, as the
    lines `env` prints."""
    return (
        "import os, pathlib\n"
        f"pathlib.Path({str(record)!r}).write_text("
        "''.join(f'{name}={value}\\n' for name, value in os.environ.items()))\n"
    )


def recording_tool(directory: Path, name: str, record: Path, output: str = "") -> Path:
    """An executable `name` in `directory` that writes its environment to `record`, prints
    `output` and succeeds; put `directory` first on PATH to stand in for the real tool."""
    directory.mkdir(parents=True, exist_ok=True)
    tool = directory / name
    tool.write_text(f"#!/bin/sh\nenv > '{record}'\nprintf '%s' '{output}'\n")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    return tool


def recorded(record: Path) -> dict[str, str]:
    """The variables a process wrote to `record`, as `environment_recorder` or `env` wrote them."""
    lines = record.read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def leaked_secrets(names: Iterable[str]) -> set[str]:
    return SECRETS.keys() & set(names)


def missing_needs(names: Iterable[str]) -> set[str]:
    return {*NEEDED} - {*names}
