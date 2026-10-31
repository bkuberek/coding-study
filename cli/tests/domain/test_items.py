"""Catalog entry kinds: the kinds of problem, and `item` (docs/specs/cli.md#cstudy-list)."""

from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.problem import ProblemKind


def test_every_kind_of_problem_is_an_entry_kind():
    assert {entry_kind(kind) for kind in ProblemKind} == set(EntryKind) - {EntryKind.ITEM}


def test_an_entry_kind_names_its_kind_of_problem():
    assert entry_kind(ProblemKind.PROJECT) == "project"
