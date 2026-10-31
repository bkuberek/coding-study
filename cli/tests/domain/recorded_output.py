"""Compiler output captured from the real toolchains, in `tests/domain/recorded/`.

Each file holds what a `DiagnosticParser` is given: the compiler lines a failed build reports
(`BuildFailed.diagnostics`, joined by newlines), with the workspace's path made `/ws`.
"""

from pathlib import Path

RECORDED = Path(__file__).parent / "recorded"


def recorded(name: str) -> str:
    return (RECORDED / name).read_text(encoding="utf-8")
