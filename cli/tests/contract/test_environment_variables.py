"""Every `CSTUDY_*` variable `cstudy` names is in one class of `domain/environment_variables.py`
(docs/specs/compatibility.md#environment-variables)."""

import ast
import re
import tokenize
from collections.abc import Iterator
from pathlib import Path

from coding_study.adapters import locations, toml_config
from coding_study.domain import environment_variables
from tests.helpers import REPOSITORY_ROOT

SOURCE = REPOSITORY_ROOT / "cli" / "src" / "coding_study"
VARIABLE = re.compile(r"CSTUDY_[A-Z0-9_]+")
CLASSES = (
    environment_variables.PUBLIC,
    environment_variables.PROBLEM_FORMAT,
    environment_variables.INTERNAL,
)


def _python_tokens(path: Path) -> Iterator[str]:
    """The variable names in the strings and comments of a Python file; a constant or a function
    that is named like a variable is not one."""
    with path.open("rb") as source:
        for token in tokenize.tokenize(source.readline):
            if token.type != tokenize.NAME:
                yield from VARIABLE.findall(token.string)


def _string_literals(path: Path) -> list[str]:
    """The strings of a Python file that are a variable name and nothing else."""
    return [
        node.value
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and VARIABLE.fullmatch(node.value)
    ]


def _tokens(path: Path) -> Iterator[str]:
    if path.suffix == ".py":
        yield from _python_tokens(path)
    else:
        yield from VARIABLE.findall(path.read_bytes().decode("latin-1"))


def _source_files() -> Iterator[Path]:
    """Every file of the package, the built page under `entrypoints/web/static/` included."""
    for path in sorted(SOURCE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def test_every_cstudy_variable_in_the_source_is_in_a_class() -> None:
    known = {name for names in CLASSES for name in names}
    unclassified = {
        f"{path.relative_to(SOURCE)}: {name}"
        for path in _source_files()
        for name in _tokens(path)
        if name not in known
    }

    assert not unclassified, (
        "classify each in coding_study/domain/environment_variables.py and in "
        f"docs/specs/compatibility.md: {sorted(unclassified)}"
    )


def test_the_scan_reads_the_files_that_are_not_python() -> None:
    names = {name for path in _source_files() if path.suffix == ".cjs" for name in _tokens(path)}

    assert "CSTUDY_HIDDEN_DIRECTORIES" in names


def test_the_scan_skips_a_name_that_is_not_in_a_string_or_a_comment(tmp_path: Path) -> None:
    file = tmp_path / "names.py"
    file.write_text('CSTUDY_CONSTANT = "x"  # CSTUDY_COMMENT\nf"{CSTUDY_VALUE}CSTUDY_TEXT"\n')

    assert sorted(_tokens(file)) == ["CSTUDY_COMMENT", "CSTUDY_TEXT"]


def test_a_variable_is_in_one_class_once() -> None:
    names = [name for group in CLASSES for name in group]

    assert len(names) == len(set(names))


def test_the_public_cstudy_variables_are_the_three_a_user_sets() -> None:
    assert [name for name in environment_variables.PUBLIC if name.startswith("CSTUDY_")] == [
        "CSTUDY_WORKSPACE",
        "CSTUDY_CONTENT",
        "CSTUDY_CONFIG",
    ]


def test_the_readers_of_public_variables_use_their_names_from_the_module() -> None:
    assert locations.WORKSPACE_VARIABLE == environment_variables.WORKSPACE
    assert locations.CONTENT_VARIABLE == environment_variables.CONTENT
    assert toml_config.CONFIG_PATH_VARIABLE == environment_variables.CONFIG
    for path in (SOURCE / "adapters" / "locations.py", SOURCE / "adapters" / "toml_config.py"):
        assert not _string_literals(path)
