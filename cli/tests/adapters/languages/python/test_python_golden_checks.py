"""Python stub goldens are user files: they must pass the workspace's own ruff and pyright.

The CLI's lint and type settings exclude tests/golden, so these checks run the tools installed in
the practice workspace's python/.venv with its configuration, where `cs_support` resolves.
"""

import subprocess
from pathlib import Path

import pytest

from tests.stub_contract import GOLDEN_ROOT

GOLDENS = sorted((GOLDEN_ROOT / "python").glob("*.py"))

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def project(practice_workspace: Path) -> Path:
    return practice_workspace / "python"


def run_tool(project: Path, tool: str, *arguments: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(project / ".venv" / "bin" / tool), *map(str, arguments)],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


def ruff(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return run_tool(project, "ruff", *arguments, "--config", "pyproject.toml", *GOLDENS)


def test_every_python_golden_is_ruff_formatted(project):
    result = ruff(project, "format", "--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_python_golden_passes_ruff_check(project):
    result = ruff(project, "check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_python_golden_type_checks(project):
    interpreter = project / ".venv" / "bin" / "python"
    result = run_tool(project, "pyright", "--pythonpath", interpreter, *GOLDENS)
    assert result.returncode == 0, result.stdout
