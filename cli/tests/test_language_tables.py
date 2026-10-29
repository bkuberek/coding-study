"""A table keyed by `Language` with a missing entry fails with a KeyError at run time, which no
type checker reports. This finds every such table in the package and requires a row per language."""

import importlib
import pkgutil
from collections.abc import Iterator, Mapping

import pytest

import coding_study
from coding_study.domain.problem import Language

KNOWN_TABLES = {
    "ALLOWED_MODELS",
    "BATCH_INPUT_BUDGETS",
    "DEFAULT_DEBUG_PORTS",
    "HELLO_TIMEOUT_MS",
    "LANGUAGE_NAMES",
    "LEXERS",
    "MEMORY_CAPS",
    "REFERENCE_LABELS",
    "RESERVED_WORDS",
    "SOURCE_EXTENSIONS",
    "WARMUPS",
}
"""Tables that exist today; the scan must find at least these, so it cannot pass by finding none."""


def language_tables() -> Iterator[tuple[str, Mapping[Language, object]]]:
    """Every module-level mapping whose keys are all languages, once per mapping object."""
    seen: set[int] = set()
    for info in pkgutil.walk_packages(coding_study.__path__, prefix=f"{coding_study.__name__}."):
        module = importlib.import_module(info.name)
        for name, value in vars(module).items():
            is_table = (
                isinstance(value, Mapping)
                and len(value) > 0
                and all(isinstance(key, Language) for key in value)
            )
            if is_table and id(value) not in seen:
                seen.add(id(value))
                yield f"{info.name}.{name}", value


TABLES = dict(language_tables())


def test_the_scan_finds_the_known_tables():
    assert {name.rpartition(".")[2] for name in TABLES} >= KNOWN_TABLES


@pytest.mark.parametrize("name", sorted(TABLES))
def test_a_language_table_has_a_row_for_every_language(name):
    assert set(TABLES[name]) == set(Language), f"{name} is missing a language"
