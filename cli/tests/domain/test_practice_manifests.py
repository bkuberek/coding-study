import tomllib

import pytest

from coding_study.domain.practice_manifests import practice_manifest, with_problem
from coding_study.domain.problem import Language
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
MANIFEST = '[package]\nname = "practice"\n\n[lib]\npath = "lib.rs"\n'
ENTRY = '[[example]]\nname = "two_sum"\npath = "practice/two_sum.rs"\ncrate-type = ["lib"]\n'


def test_only_rust_keeps_a_manifest_of_problems():
    manifests = {language: practice_manifest(language) for language in Language}
    assert {language for language, path in manifests.items() if path} == {Language.RUST}
    assert manifests[Language.RUST] == "rust/Cargo.toml"


def test_adds_the_problem_as_a_library_example():
    assert with_problem(MANIFEST, TWO_SUM) == f"{MANIFEST}\n{ENTRY}"


def test_the_result_is_valid_toml():
    examples = tomllib.loads(with_problem(MANIFEST, TWO_SUM))["example"]
    assert examples == [{"name": "two_sum", "path": "practice/two_sum.rs", "crate-type": ["lib"]}]


@pytest.mark.parametrize(
    "existing",
    [ENTRY, '[[example]]\nname = "two_sum"\npath = "elsewhere.rs"\n'],
    ids=["same entry", "same name"],
)
def test_a_listed_problem_is_left_as_it_is(existing):
    manifest = f"{MANIFEST}\n{existing}"
    assert with_problem(manifest, TWO_SUM) == manifest


def test_a_manifest_without_a_final_newline_gets_a_blank_line():
    assert with_problem(MANIFEST.rstrip("\n"), TWO_SUM) == f"{MANIFEST}\n{ENTRY}"


def test_a_manifest_that_does_not_parse_is_unchanged():
    assert with_problem("[package\n", TWO_SUM) == "[package\n"
