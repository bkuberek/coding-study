"""Whether a tool can run here, for the tests that skip without it."""

import shutil
import subprocess
from collections.abc import Callable, Iterable
from typing import Any

import pytest

VERSION_TIMEOUT_SECONDS = 30.0
JVM_LANGUAGES = ("java", "kotlin")


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


def jvm_marked[T](values: Iterable[T], language_of: Callable[[T], str] = str) -> list[Any]:
    """`values` as test parameters with the Java and Kotlin ones marked `jvm`, for a slow test over
    every language: CI selects the JVM rows with `-m jvm` and runs them on the JDKs of the range."""
    return [
        pytest.param(value, marks=pytest.mark.jvm) if language_of(value) in JVM_LANGUAGES else value
        for value in values
    ]
