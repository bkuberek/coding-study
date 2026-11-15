"""The kinds of catalog entry: autograded and rubric (docs/specs/cli.md#cstudy-list)."""

from coding_study.domain.items import RUBRIC_KINDS, EntryKind, ItemMeta, entry_kind, is_rubric_track
from coding_study.domain.problem import ContentStatus, Difficulty, ProblemKind, Track


def test_every_kind_of_problem_is_an_entry_kind():
    assert {entry_kind(kind) for kind in ProblemKind} == set(EntryKind) - set(RUBRIC_KINDS)


def test_an_entry_kind_names_its_kind_of_problem():
    assert entry_kind(ProblemKind.PROJECT) == "project"


def test_the_rubric_kinds_are_system_design_and_code_review():
    assert RUBRIC_KINDS == (EntryKind.SYSTEM_DESIGN, EntryKind.CODE_REVIEW)


def test_a_rubric_track_is_the_track_of_a_rubric_kind():
    assert {track for track in Track if is_rubric_track(track)} == {
        Track.SYSTEM_DESIGN,
        Track.CODE_REVIEW,
    }


def test_a_rubric_problem_has_the_kind_of_its_track():
    meta = ItemMeta(
        "retry-wrapper",
        "Retry Wrapper",
        Track.CODE_REVIEW,
        Difficulty.EASY,
        20,
        ContentStatus.READY,
    )
    assert meta.kind is EntryKind.CODE_REVIEW


def test_a_rubric_problem_lists_in_the_catalog_after_the_problems_of_earlier_tracks():
    design = ItemMeta(
        "url-shortener",
        "URL Shortener",
        Track.SYSTEM_DESIGN,
        Difficulty.MEDIUM,
        45,
        ContentStatus.READY,
    )
    review = ItemMeta(
        "retry-wrapper",
        "Retry Wrapper",
        Track.CODE_REVIEW,
        Difficulty.EASY,
        20,
        ContentStatus.READY,
    )
    assert sorted([review, design], key=lambda meta: meta.listing_key()) == [design, review]
    assert design.listing_key()[0] is False
