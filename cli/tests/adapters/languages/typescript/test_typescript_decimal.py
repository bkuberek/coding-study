"""The `Decimal` class of runners/typescript/support.ts, through Node's own test runner."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

DECIMAL_TESTS = Path(__file__).resolve().parent / "decimal.test.ts"
TIMEOUT_SECONDS = 120


def test_node_runs_every_decimal_test_successfully():
    result = subprocess.run(
        ["node", "--test", str(DECIMAL_TESTS)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
