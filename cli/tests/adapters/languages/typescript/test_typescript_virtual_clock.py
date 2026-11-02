"""The virtual clock of runners/typescript/lib/virtual-clock.ts, through Node's own test runner,
as a project's tests run its copy (docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

CLOCK_TESTS = Path(__file__).resolve().parent / "virtual-clock.test.ts"
TIMEOUT_SECONDS = 120


def test_node_runs_every_virtual_clock_test_successfully():
    result = subprocess.run(
        ["node", "--test", str(CLOCK_TESTS)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
