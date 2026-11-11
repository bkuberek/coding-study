"""feed-ingest-python states its points bands and its reject reasons in `problem.md`, and its cases
and reference use them. These tests keep the three in step, and keep the cases that wait on a slow
partner well inside their limit."""

import json
import re
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0312-feed-ingest-python"
STATEMENT = (PROBLEM / "problem.md").read_text(encoding="utf-8")
POINTS_SOURCE = (PROBLEM / "solutions" / "reference" / "src" / "points.py").read_text(
    encoding="utf-8"
)
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
CASES = {case["id"]: case for case in TESTS["cases"]}

type Band = tuple[int | None, int]

ATTEMPT_TIMEOUT_MS = 1000
ATTEMPTS = 3
PAUSES_MS = 200 + 400


def statement_bands() -> dict[str, list[Band]]:
    """The points table of level 3, row by row: (upper edge of the band or None, percent)."""
    bands: dict[str, list[Band]] = {}
    pattern = re.compile(r"\| `(\w+)` \| (.+?) \| (\d+) \|")
    for category, spending, percent in pattern.findall(STATEMENT):
        edge = re.search(r"(?:first|to) ([\d,]+) cents|from [\d,]+ to ([\d,]+)", spending)
        upper = int((edge[1] or edge[2]).replace(",", "")) if edge else None
        bands.setdefault(category, []).append((upper, int(percent)))
    return bands


def reference_bands() -> dict[str, list[Band]]:
    block = re.search(r"BANDS: [^=]+= \{(.*?)\n\}", POINTS_SOURCE, re.S)
    assert block is not None
    bands: dict[str, list[Band]] = {}
    for category, body in re.findall(r'"(\w+)": \[(.*?)\],\n', block[1] + "\n", re.S):
        pairs = re.findall(r"\((None|[\d_]+), (\d+)\)", body)
        bands[category] = [
            (None if edge == "None" else int(edge.replace("_", "")), int(percent))
            for edge, percent in pairs
        ]
    return bands


def test_the_reference_pays_the_bands_the_statement_lists():
    assert reference_bands() == statement_bands()


def test_the_statement_lists_all_five_categories():
    assert sorted(statement_bands()) == ["dining", "fuel", "grocery", "other", "travel"]


def reasons_in_statement() -> set[str]:
    return set(re.findall(r"^\| `([a-z]+(?:_[a-z]+)+)` \|", STATEMENT, re.M))


def reasons_in_cases() -> Iterator[str]:
    for case in TESTS["cases"]:
        for step in case.get("steps", []):
            body = step.get("expected", {}).get("body")
            if isinstance(body, list):
                yield from (
                    row["reason"] for row in body if isinstance(row, dict) and "reason" in row
                )


def test_every_reason_a_case_expects_is_one_the_statement_explains():
    assert set(reasons_in_cases()) <= reasons_in_statement()


def test_every_reason_the_statement_explains_is_expected_by_some_case():
    assert reasons_in_statement() <= set(reasons_in_cases())


SLOW_CASES = sorted(
    case_id
    for case_id, case in CASES.items()
    if (case.get("mocks") or {}).get("bonus-partner") == "ana_slow"
)


@pytest.mark.parametrize("case_id", SLOW_CASES)
def test_a_lookup_that_times_out_leaves_its_case_half_its_limit(case_id: str):
    """`ana_slow` is asked about three times, each given up on after a second, with two pauses."""
    assert CASES[case_id]["hang_guard_ms"] / 2 >= ATTEMPTS * ATTEMPT_TIMEOUT_MS + PAUSES_MS
