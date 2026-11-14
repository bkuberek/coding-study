"""Every example of every concept guide runs and prints exactly what its guide says it prints
(docs/specs/guides.md#examples), so an example cannot rot.

Each example runs from a copy in a folder of its own, so it writes nothing into the checkout.
Python and JavaScript run in the fast suite; Go and Java are slow (Java also `jvm`), and a language
whose toolchain is missing is skipped, as is a Python example that calls `os.fork` where the
platform has no `os.fork`.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.guide_markdown import GuideMarkdown
from tests.helpers import REPOSITORY_ROOT

GUIDES = REPOSITORY_ROOT / "guides"
TIMEOUT_SECONDS = 180.0
"""Generous: a cold `go run` or `java` start on a busy machine takes seconds."""
COMMANDS: dict[str, list[str]] = {
    ".py": [sys.executable, "-I", "-B"],
    ".js": ["node"],
    ".mjs": ["node"],
    ".go": ["go", "run"],
    ".java": ["java"],
}
TOOLS = {".js": "node", ".mjs": "node", ".go": "go", ".java": "java"}
SLOW = {".go": (pytest.mark.slow,), ".java": (pytest.mark.slow, pytest.mark.jvm)}


def documented_examples() -> Iterator[Any]:
    for folder in sorted(GUIDES.iterdir()):
        markdown_file = folder / "guide.md"
        if not markdown_file.is_file():
            continue
        markdown = GuideMarkdown(markdown_file.read_text(encoding="utf-8"))
        outputs = {fence.argument: fence.content for fence in markdown.output_fences()}
        for fence in markdown.example_fences():
            name = fence.argument or ""
            suffix = Path(name).suffix
            yield pytest.param(
                folder / name,
                outputs.get(name),
                id=f"{folder.name}/{name}",
                marks=SLOW.get(suffix, ()),
            )


def test_the_guides_have_examples():
    assert len(list(documented_examples())) > 0


@pytest.mark.parametrize(("example", "documented"), list(documented_examples()))
def test_an_example_prints_what_its_guide_says(
    example: Path, documented: str | None, tmp_path: Path
):
    tool = TOOLS.get(example.suffix)
    if tool is not None and shutil.which(tool) is None:
        pytest.skip(f"{tool} is not installed")
    needs_fork = example.suffix == ".py" and "os.fork(" in example.read_text(encoding="utf-8")
    if needs_fork and not hasattr(os, "fork"):
        pytest.skip("needs os.fork, a POSIX call")
    copy = tmp_path / example.name
    shutil.copyfile(example, copy)
    result = subprocess.run(
        [*COMMANDS[example.suffix], copy.name],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert (result.returncode, result.stderr, result.stdout) == (0, "", documented)
