"""safe-redaction-python hands its methods the starter extractor's own proposals in some cases,
and gives the two patterns of level 3 in `problem.md`. These tests keep the cases equal to what the
extractor says, and the statement equal to the reference's patterns."""

import json
import re
import sys
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0315-safe-redaction-python"
STARTER = PROBLEM / "starter"
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
STATEMENT = (PROBLEM / "problem.md").read_text(encoding="utf-8")
NET_SOURCE = (PROBLEM / "solutions" / "reference" / "redaction" / "net.py").read_text(
    encoding="utf-8"
)
EXTRACTED = "(extractor output)"
PROPOSAL_METHODS = {"redactProposed", "redactSafely", "evaluate"}


@pytest.fixture
def propose(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The starter's extractor, imported without leaving a cache in the starter's folder."""
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.syspath_prepend(str(STARTER))
    from redaction.extractor import propose as function  # pyright: ignore[reportMissingImports]

    yield function
    for name in [name for name in sys.modules if name.split(".")[0] == "redaction"]:
        del sys.modules[name]


def extracted_calls() -> Iterator[tuple[str, list[Any]]]:
    for case in TESTS["cases"]:
        if EXTRACTED not in case["note"]:
            continue
        for method, args in zip(case["ops"][1:], case["args"][1:], strict=True):
            if method in PROPOSAL_METHODS:
                yield case["id"], args


def test_the_cases_marked_as_extractor_output_exist():
    assert {case_id for case_id, _ in extracted_calls()} >= {"ex3", "ex4", "ex5", "ex6", "ex8"}


@pytest.mark.parametrize(("case_id", "args"), list(extracted_calls()), ids=lambda v: str(v)[:12])
def test_a_case_marked_as_extractor_output_holds_what_the_extractor_proposes(
    propose: Any, case_id: str, args: list[Any]
):
    text, starts, ends, labels, quotes = args[:5]
    proposals = propose(text)

    assert (starts, ends, labels, quotes) == (
        [p.start for p in proposals],
        [p.end for p in proposals],
        [p.label for p in proposals],
        [p.quote for p in proposals],
    )


@pytest.mark.parametrize("name", ["EMAIL", "PHONE"])
def test_the_statement_gives_the_pattern_the_reference_uses(name: str):
    in_statement = re.search(rf'^{name} = r"(.+)"$', STATEMENT, re.M)
    in_reference = re.search(rf'{name} = re\.compile\(\s*r"(.+)"\s*\)', NET_SOURCE)

    assert in_statement is not None
    assert in_reference is not None
    assert in_statement[1] == in_reference[1]


def test_every_span_of_a_level_1_case_is_inside_its_text():
    for case in TESTS["cases"]:
        if case["level"] != 1:
            continue
        for args in case["args"][1:]:
            text, starts, ends = args[:3]
            assert all(
                0 <= start < end <= len(text) for start, end in zip(starts, ends, strict=True)
            )
