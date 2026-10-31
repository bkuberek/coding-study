"""A project statement's `Methods to add:` line spells types as the language's stubs do, except a
TypeScript date: a project folder cannot import the runner's `IsoDate`, so it is a `string`."""

import pytest

from coding_study.adapters.languages.python.stub_generator import python_type
from coding_study.adapters.languages.typescript.stub_generator import typescript_type
from coding_study.domain.problem import Language
from coding_study.domain.project import method_text
from coding_study.domain.type_dsl import parse_return_type
from tests.project_builders import method

TYPES = (
    "void",
    "int",
    "long",
    "double",
    "bool",
    "string",
    "char",
    "decimal",
    "int[]",
    "string[][]",
    "list<long>",
    "list<list<double>>",
    "list<decimal>",
)


@pytest.mark.parametrize("type_text", [*TYPES, "date", "list<date>"])
def test_python_methods_read_as_the_python_stub_declares_them(type_text):
    declared = method("snapshot", 1, returns=type_text)
    expected = python_type(parse_return_type(type_text))
    assert method_text(declared, Language.PYTHON) == f"snapshot() -> {expected}"


@pytest.mark.parametrize("type_text", TYPES)
def test_typescript_methods_read_as_the_typescript_stub_declares_them(type_text):
    declared = method("snapshot", 1, returns=type_text)
    expected = typescript_type(parse_return_type(type_text))
    assert method_text(declared, Language.TYPESCRIPT) == f"snapshot(): {expected}"
