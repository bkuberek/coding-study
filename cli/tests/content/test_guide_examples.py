"""Every example of every concept guide, each variant of an example in several languages too,
runs and prints exactly what its guide says it prints (docs/specs/guides.md#examples), so an
example cannot rot.

Each example runs from a copy in a folder of its own, so it writes nothing into the checkout.
Python, TypeScript, JavaScript and bash run in the fast suite; Go, Rust, Java and Kotlin are slow
(Java and Kotlin also `jvm`), and a language whose tools are missing is skipped, as is a Python
example that calls `os.fork` where the platform has no `os.fork`.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.guide_examples import EXAMPLE_LANGUAGES, suffix
from coding_study.domain.guide_markdown import GuideMarkdown
from tests.helpers import REPOSITORY_ROOT

GUIDES = REPOSITORY_ROOT / "guides"
TIMEOUT_SECONDS = 180.0
"""Generous: a cold `go run`, `kotlinc` or `java` start on a busy machine takes seconds."""
PROGRAM = "program"
"""What a compiled Rust example is called in its folder."""
RUST_EDITION = "2021"


def steps(file: str) -> list[list[str]]:
    """The commands that run the example `file` from its folder, in order; the last one's output
    is the example's."""
    match suffix(file):
        case ".py":
            return [[sys.executable, "-I", "-B", file]]
        case ".ts" | ".js" | ".mjs":
            return [["node", file]]
        case ".sh":
            return [["bash", file]]
        case ".go":
            return [["go", "run", file]]
        case ".java":
            return [["java", file]]
        case ".kt":
            jar = f"{file}.jar"
            return [["kotlinc", file, "-include-runtime", "-d", jar], ["java", "-jar", jar]]
        case ".rs":
            return [["rustc", "--edition", RUST_EDITION, "-o", PROGRAM, file], [f"./{PROGRAM}"]]
        case other:
            raise AssertionError(f"no way to run a {other} example")


TOOLS: dict[str, tuple[str, ...]] = {
    ".ts": ("node",),
    ".js": ("node",),
    ".mjs": ("node",),
    ".sh": ("bash",),
    ".go": ("go",),
    ".java": ("java",),
    ".kt": ("kotlinc", "java"),
    ".rs": ("rustc",),
}
SLOW = {
    ".go": (pytest.mark.slow,),
    ".rs": (pytest.mark.slow,),
    ".java": (pytest.mark.slow, pytest.mark.jvm),
    ".kt": (pytest.mark.slow, pytest.mark.jvm),
}


def documented_examples() -> Iterator[Any]:
    for folder in sorted(GUIDES.iterdir()):
        markdown_file = folder / "guide.md"
        if not markdown_file.is_file():
            continue
        markdown = GuideMarkdown(markdown_file.read_text(encoding="utf-8"))
        outputs = {fence.argument: fence.content for fence in markdown.output_fences()}
        for fence in markdown.example_fences():
            name = fence.argument or ""
            yield pytest.param(
                folder / name,
                outputs.get(name),
                id=f"{folder.name}/{name}",
                marks=SLOW.get(suffix(name), ()),
            )


def test_the_guides_have_examples():
    assert len(list(documented_examples())) > 0


def test_every_language_an_example_may_be_written_in_has_a_way_to_run():
    assert all(steps(f"example{extension}") for extension in EXAMPLE_LANGUAGES)


@pytest.mark.parametrize(("example", "documented"), list(documented_examples()))
def test_an_example_prints_what_its_guide_says(
    example: Path, documented: str | None, tmp_path: Path
):
    for tool in TOOLS.get(example.suffix, ()):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} is not installed")
    needs_fork = example.suffix == ".py" and "os.fork(" in example.read_text(encoding="utf-8")
    if needs_fork and not hasattr(os, "fork"):
        pytest.skip("needs os.fork, a POSIX call")
    copy = tmp_path / example.name
    shutil.copyfile(example, copy)
    *build, run = steps(copy.name)
    for command in build:
        built = subprocess.run(
            command,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        assert built.returncode == 0, built.stderr
    result = subprocess.run(
        run,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert (result.returncode, result.stderr, result.stdout) == (0, "", documented)
