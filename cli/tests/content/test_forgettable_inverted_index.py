"""forgettable-inverted-index ranks memories by floating-point BM25 scores. These tests replay every
case against an index rebuilt from scratch on each call, which derives the expected values a
second way, and prove that no expected ranking hangs on rounding: two documents that rank next to
each other, or on either side of the topN cut, either hold the same counts of the query's tokens
and have the same length, so that they tie in every order of addition, or score far apart."""

import itertools
import json
import math
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0297-forgettable-inverted-index"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCORE_TOLERANCE = 1e-9
"""Far below the grader's 1e-6, and far above the rounding of a sum of 20 terms."""


@dataclass
class RebuiltIndex:
    """The documents alone; every statistic is computed again on each call."""

    k1: float
    b: float
    documents: dict[str, list[str]] = field(default_factory=dict)

    def scores(self, query: Sequence[str]) -> dict[str, float]:
        count = len(self.documents)
        total_length = sum(len(tokens) for tokens in self.documents.values())
        scores: dict[str, float] = {}
        for term in set(query):
            holders = {
                doc_id: tokens.count(term)
                for doc_id, tokens in self.documents.items()
                if term in tokens
            }
            idf = math.log(1 + (count - len(holders) + 0.5) / (len(holders) + 0.5))
            for doc_id, tf in holders.items():
                length_ratio = len(self.documents[doc_id]) / (total_length / count)
                saturation = tf + self.k1 * (1 - self.b + self.b * length_ratio)
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * tf * (self.k1 + 1) / saturation
        return scores

    def ranking(self, query: Sequence[str]) -> list[str]:
        scores = self.scores(query)
        return sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))

    def profile(self, query: Sequence[str], doc_id: str) -> tuple[int, ...]:
        """What a score depends on besides the index-wide statistics: the length only when b is
        not 0, since b * |d| / avgdl is then exactly 0 in every way of writing it."""
        tokens = self.documents[doc_id]
        length = len(tokens) if self.b else 0
        return (length, *(tokens.count(term) for term in sorted(set(query))))

    def call(self, op: str, arguments: Sequence[Any]) -> Any:
        match op:
            case "add":
                doc_id, tokens = arguments
                if doc_id in self.documents:
                    return False
                self.documents[doc_id] = list(tokens)
                return True
            case "update":
                doc_id, tokens = arguments
                if doc_id not in self.documents:
                    return False
                self.documents[doc_id] = list(tokens)
                return True
            case "forget":
                return self.documents.pop(arguments[0], None) is not None
            case "search":
                query, top_n = arguments
                return self.ranking(query)[:top_n]
            case "score":
                query, doc_id = arguments
                return self.scores(query).get(doc_id, 0.0)
        raise AssertionError(f"unknown op {op}")


def replay(case: Mapping[str, Any]) -> Iterator[tuple[str, Sequence[Any], Any, RebuiltIndex]]:
    """Each call after the constructor: its op, arguments, output, and the index right after it."""
    index = RebuiltIndex(*case["args"][0])
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        yield op, arguments, index.call(op, arguments), index


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_every_expected_output_follows_from_the_documents_alone(case):
    outputs = [output for _, _, output, _ in replay(case)]
    for output, expected in zip(outputs, case["expected"][1:], strict=True):
        if isinstance(expected, float):
            assert math.isclose(output, expected, rel_tol=SCORE_TOLERANCE)
        else:
            assert output == expected


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_no_expected_ranking_hangs_on_rounding(case):
    for op, arguments, _, index in replay(case):
        if op != "search":
            continue
        query, top_n = arguments
        scores = index.scores(query)
        ranking = index.ranking(query)[: top_n + 1]
        for higher, lower in itertools.pairwise(ranking):
            close = math.isclose(scores[higher], scores[lower], rel_tol=SCORE_TOLERANCE)
            same = index.profile(query, higher) == index.profile(query, lower)
            assert close == same, f"{case['id']}: {higher} and {lower} for {query}"
