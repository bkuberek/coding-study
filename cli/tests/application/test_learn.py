"""`cstudy learn`: guides, paths and how far a learner has come (docs/specs/guides.md)."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.learn import (
    LearnListing,
    ListingFilter,
    guide_page,
    learn_listing,
    mark_read,
    narrow_listing,
    path_view,
)
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.concept_guides import GuideLevel, GuideStatus
from coding_study.domain.config import Config
from coding_study.domain.errors import UnknownGuideError
from coding_study.domain.problem import Language
from tests.fakes import NOW, FakeClock, make_environment
from tests.guide_builders import write_guide, write_hashing, write_path

LEDGER_LEVELS = 4


@pytest.fixture
def environment(content_root: Path) -> Environment:
    write_hashing(content_root)
    write_guide(content_root, "a-loose-guide", "A loose guide")
    return make_environment(content_root)


def attempt(
    environment: Environment,
    slug: str,
    status: AttemptStatus,
    level_unlocked: int | None = None,
    levels_passed: int | None = None,
) -> None:
    progress = environment.progress
    started = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    ended = None if status is AttemptStatus.IN_PROGRESS else NOW
    grade = Grade.OK if status is AttemptStatus.PASSED else None
    progress.update_attempt(
        replace(
            started,
            status=status,
            ended_at=ended,
            grade=grade,
            level_unlocked=level_unlocked,
            levels_passed=levels_passed,
            levels_total=None if levels_passed is None else LEDGER_LEVELS,
        )
    )


def test_the_list_puts_the_guides_of_paths_first_in_path_order(environment: Environment):
    listing = learn_listing(environment)
    assert [entry.meta.slug for entry in listing.guides] == [
        "hash-functions",
        "hash-maps",
        "a-loose-guide",
    ]


def test_the_listing_and_a_guide_page_carry_the_guides_labels(
    environment: Environment, content_root: Path
):
    write_guide(content_root, "labeled", "Labeled", domains=("data",), job_roles=("data-engineer",))
    listed = next(
        entry.meta for entry in learn_listing(environment).guides if entry.meta.slug == "labeled"
    )
    page = guide_page(environment, "labeled").entry.meta
    assert [(meta.domains, meta.job_roles) for meta in (listed, page)] == [
        (("data",), ("data-engineer",))
    ] * 2


def test_the_list_orders_the_paths_from_introductory_to_advanced(
    environment: Environment, content_root: Path
):
    write_guide(content_root, "merkle-trees", "Merkle trees", level="advanced")
    write_guide(content_root, "consistent-hashing", "Consistent hashing", level="core")
    write_path(
        content_root,
        "deep-hashing",
        ["guide: consistent-hashing", "guide: merkle-trees"],
        title="Deep hashing",
    )
    write_path(content_root, "problems-only", ["problem: two-sum"], title="Problems only")
    listing = learn_listing(environment)
    assert [(view.path.slug, view.level) for view in listing.paths] == [
        ("hashing", GuideLevel.INTRO),
        ("deep-hashing", GuideLevel.ADVANCED),
        ("problems-only", None),
    ]


def test_the_guides_of_paths_follow_the_order_of_the_paths(
    environment: Environment, content_root: Path
):
    write_guide(content_root, "merkle-trees", "Merkle trees", level="advanced")
    write_path(content_root, "advanced-first", ["guide: merkle-trees"], title="Advanced")
    listing = learn_listing(environment)
    assert [entry.meta.slug for entry in listing.guides] == [
        "hash-functions",
        "hash-maps",
        "merkle-trees",
        "a-loose-guide",
    ]


def test_a_path_that_names_its_level_is_ordered_by_it(environment: Environment, content_root: Path):
    write_guide(content_root, "merkle-trees", "Merkle trees", level="advanced")
    write_path(content_root, "a-gentle-start", ["guide: merkle-trees"], level="intro")
    write_path(content_root, "hashing", ["guide: hash-functions"], level="advanced")
    assert [(view.path.slug, view.level) for view in learn_listing(environment).paths] == [
        ("a-gentle-start", GuideLevel.INTRO),
        ("hashing", GuideLevel.ADVANCED),
    ]


def shown(listing: LearnListing) -> tuple[list[str], list[str]]:
    return [entry.meta.slug for entry in listing.guides], [view.path.slug for view in listing.paths]


def test_the_list_narrows_to_a_search_a_level_or_a_status(
    environment: Environment, content_root: Path
):
    write_guide(content_root, "merkle-trees", "Merkle trees", level="advanced")
    write_path(content_root, "deep-hashing", ["guide: merkle-trees"], title="Deep hashing")
    mark_read(environment, "hash-functions")
    listing = learn_listing(environment)
    assert [
        shown(narrow_listing(listing, ListingFilter(search="HASH  maps"))),
        shown(narrow_listing(listing, ListingFilter(level=GuideLevel.ADVANCED))),
        shown(narrow_listing(listing, ListingFilter(status=GuideStatus.READ))),
        shown(narrow_listing(listing, ListingFilter(status=GuideStatus.NOT_READ))),
    ] == [
        (["hash-maps"], []),
        (["merkle-trees"], ["deep-hashing"]),
        (["hash-functions"], []),
        (["hash-maps", "merkle-trees", "a-loose-guide"], ["hashing", "deep-hashing"]),
    ]


def test_the_search_the_level_and_the_status_combine(environment: Environment):
    mark_read(environment, "hash-functions")
    wanted = ListingFilter(search="hash", level=GuideLevel.INTRO, status=GuideStatus.NOT_READ)
    assert shown(narrow_listing(learn_listing(environment), wanted)) == (["hash-maps"], ["hashing"])


def test_a_path_on_its_own_has_its_level(environment: Environment):
    assert path_view(environment, "hashing").level is GuideLevel.INTRO


def test_the_list_counts_each_paths_steps(environment: Environment):
    mark_read(environment, "hash-functions")
    (view,) = learn_listing(environment).paths
    assert (view.path.slug, view.done, view.total) == ("hashing", 1, 4)


def test_a_guide_page_shows_the_diagrams_as_text(environment: Environment):
    page = guide_page(environment, "hash-maps")
    assert ("```mermaid" in page.markdown, "```mermaid" in page.terminal_text()) == (True, False)


def test_a_guide_page_shows_each_example_in_the_language_chosen_else_default_lang(
    content_root: Path,
):
    write_guide(content_root, "hash-maps", "Hash maps", variants=True)
    environment = make_environment(content_root, config=Config(default_lang=Language.GO))
    shown = guide_page(environment, "hash-maps").terminal_text("hint")
    chosen = guide_page(environment, "hash-maps", language="typescript").terminal_text("hint")
    assert (
        "```go examples/hello.go" in shown,
        "```python examples/hello.py" in shown,
        "Also in python, typescript: hint" in shown,
        "```typescript examples/hello.ts" in chosen,
        "Also in python, go: hint" in chosen,
    ) == (True, False, True, True, True)


def test_a_guide_page_names_its_examples(environment: Environment, content_root: Path):
    page = guide_page(environment, "hash-maps")
    folder = content_root / "guides" / "hash-maps" / "examples"
    assert (page.examples, page.examples_folder) == ((folder / "hello.py",), folder)


def test_an_unknown_guide_suggests_the_nearest(environment: Environment):
    with pytest.raises(UnknownGuideError, match='unknown guide "hash-map"; did you mean hash-maps'):
        guide_page(environment, "hash-map")


def test_marking_a_guide_read_keeps_the_first_time(environment: Environment):
    first = mark_read(environment, "hash-maps")
    clock = environment.clock
    assert isinstance(clock, FakeClock)
    clock.advance(timedelta(days=2))
    again = mark_read(environment, "hash-maps")
    assert (first.already, again.already, again.read_at) == (False, True, first.read_at)


def test_a_marked_guide_reads_as_read(environment: Environment):
    mark_read(environment, "hash-maps")
    assert guide_page(environment, "hash-maps").entry.read_at == NOW


def test_marking_an_unknown_guide_records_nothing(environment: Environment):
    with pytest.raises(UnknownGuideError):
        mark_read(environment, "nope")
    assert environment.progress.guide_reads() == {}


def test_a_new_path_has_nothing_done_and_starts_at_its_first_step(environment: Environment):
    view = path_view(environment, "hashing")
    assert (view.done, view.next_step and view.next_step.step.slug) == (0, "hash-functions")


def test_a_path_counts_read_guides_and_passed_problems(environment: Environment):
    mark_read(environment, "hash-functions")
    mark_read(environment, "hash-maps")
    attempt(environment, "two-sum", AttemptStatus.PASSED)
    view = path_view(environment, "hashing")
    assert [(step.done, step.status) for step in view.steps] == [
        (True, "read"),
        (True, "read"),
        (True, "passed"),
        (False, "new"),
    ]


def test_a_level_target_is_done_once_an_attempt_passed_that_level(environment: Environment):
    attempt(environment, "tamper-evident-ledger", AttemptStatus.IN_PROGRESS, level_unlocked=3)
    step = path_view(environment, "hashing").steps[3]
    assert (step.done, step.status, step.level_passed, step.title) == (
        True,
        "level 2 passed",
        2,
        "Tamper-Evident Ledger",
    )


def test_a_level_target_not_reached_shows_how_far_it_got(environment: Environment):
    attempt(environment, "tamper-evident-ledger", AttemptStatus.ABANDONED, level_unlocked=2)
    step = path_view(environment, "hashing").steps[3]
    assert (step.done, step.status) == (False, "level 1 passed")


def test_a_pass_below_a_level_target_leaves_it_to_do(environment: Environment):
    attempt(environment, "tamper-evident-ledger", AttemptStatus.PASSED, 2, levels_passed=1)
    step = path_view(environment, "hashing").steps[3]
    assert (step.done, step.status, step.level_passed) == (False, "level 1 passed", 1)


def test_a_pass_through_a_level_target_meets_it(environment: Environment):
    attempt(environment, "tamper-evident-ledger", AttemptStatus.PASSED, 2, levels_passed=2)
    step = path_view(environment, "hashing").steps[3]
    assert (step.done, step.status) == (True, "level 2 passed")


def test_a_problem_step_without_a_level_needs_every_level(
    environment: Environment, content_root: Path
):
    write_path(content_root, "ledger", ["problem: tamper-evident-ledger"], title="Ledger")
    attempt(environment, "tamper-evident-ledger", AttemptStatus.PASSED, 3, levels_passed=3)
    (part,) = path_view(environment, "ledger").steps
    attempt(environment, "tamper-evident-ledger", AttemptStatus.PASSED, 4, levels_passed=4)
    (whole,) = path_view(environment, "ledger").steps
    assert [(step.done, step.status) for step in (part, whole)] == [
        (False, "level 3 passed"),
        (True, "passed"),
    ]


def test_a_failed_problem_reads_as_attempted(environment: Environment):
    attempt(environment, "two-sum", AttemptStatus.FAILED)
    assert path_view(environment, "hashing").steps[2].status == "attempted"


def test_an_unknown_path_says_where_the_paths_are(environment: Environment):
    with pytest.raises(UnknownGuideError, match='unknown path "zzz"; cstudy learn lists the paths'):
        path_view(environment, "zzz")
