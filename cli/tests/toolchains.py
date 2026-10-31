"""Whether a tool can run here, for the tests that skip without it."""

import shutil
import subprocess

import pytest

VERSION_TIMEOUT_SECONDS = 30.0


def tool_works(name: str) -> bool:
    """On PATH is not enough: rustup puts a stub for `rustfmt` there even when the component is
    missing, and the stub fails when run."""
    path = shutil.which(name)
    if path is None:
        return False
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            check=False,
            timeout=VERSION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


needs_rustfmt = pytest.mark.skipif(not tool_works("rustfmt"), reason="rustfmt is not installed")
