"""Every `CSTUDY_*` variable `cstudy` names is in one class of `domain/environment_variables.py`
(docs/specs/compatibility.md#environment-variables)."""

import ast
import re
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


def _literals(path: Path) -> Iterator[str]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and VARIABLE.fullmatch(node.value)
        ):
            yield node.value


def test_every_cstudy_variable_literal_in_the_source_is_in_a_class() -> None:
    known = {name for names in CLASSES for name in names}
    unclassified = {
        f"{path.relative_to(SOURCE)}: {name}"
        for path in SOURCE.rglob("*.py")
        for name in _literals(path)
        if name not in known
    }

    assert not unclassified, (
        "classify each in coding_study/domain/environment_variables.py and in "
        f"docs/specs/compatibility.md: {sorted(unclassified)}"
    )


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
        assert list(_literals(path)) == []
