"""`cstudy learn`: guides, paths and how far a learner has come (docs/specs/guides.md)."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.learn import (
    LearnListing,
    ListingFilter,
    ProfiledListing,
    guide_page,
    label_scope,
    learn_listing,
    mark_read,
    narrow_listing,
    path_view,
    profiled_listing,
)
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.concept_guides import GuideLevel, GuideStatus
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.errors import UnknownGuideError
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import Language
from coding_study.domain.profile import widening_from
from coding_study.domain.taxonomy import DOMAINS, PROFILE_JOB_ROLES
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


# The learner profile, `--domain`, `--role` and `--widen` (docs/specs/cli.md#matching)


NO_FILTER = ListingFilter()


@pytest.fixture
def labeled(environment: Environment, content_root: Path) -> Environment:
    """Hashing's guides are algorithms for any engineer; four more, and paths of their own."""
    write_guide(content_root, "tls", "TLS", domains=("security",), job_roles=("security-engineer",))
    write_guide(content_root, "etl", "ETL", domains=("data",), job_roles=("data-engineer",))
    write_guide(content_root, "basics", "Basics", domains=("algorithms",), job_roles=("general",))
    write_guide(content_root, "apis", "APIs", domains=("backend", "data"), job_roles=("backend",))
    write_path(content_root, "secure", ["guide: tls", "guide: etl"], title="Secure")
    write_path(content_root, "pipelines", ["guide: etl"], title="Pipelines")
    write_path(content_root, "problem-steps", ["problem: two-sum", "problem: gone"], title="Steps")
    return make_environment(content_root)


def profiled(
    environment: Environment,
    *,
    domains: tuple[str, ...] = DOMAINS,
    roles: tuple[str, ...] = PROFILE_JOB_ROLES,
    domain: str | None = None,
    role: str | None = None,
    widen: tuple[str, ...] = (),
    wanted: ListingFilter = NO_FILTER,
) -> ProfiledListing:
    config = Config(profile=ProfileSettings(job_roles=roles, domains=domains))
    configured = replace(environment, config=config)
    scope = label_scope(configured, LabelFilter(domain, role), widening_from(widen))
    return profiled_listing(learn_listing(configured), wanted, scope)


def test_a_default_profile_lists_everything_and_hides_nothing(labeled: Environment):
    result = profiled(labeled)
    assert (shown(result.listing), result.narrowed.is_empty) == (
        shown(learn_listing(labeled)),
        True,
    )
    assert (result.hidden_guides, result.hidden_paths) == (0, 0)


def test_a_domain_profile_keeps_the_guides_that_list_one(
    labeled: Environment,
):
    guides, paths = shown(profiled(labeled, domains=("security",)).listing)
    assert (guides, paths) == (["tls"], ["hashing", "secure"])


def test_a_guide_listing_one_of_its_domains_matches(labeled: Environment):
    guides, _ = shown(profiled(labeled, domains=("backend",)).listing)
    assert ("apis" in guides, "etl" in guides) == (True, False)


def test_a_path_matches_through_any_of_its_steps(labeled: Environment):
    result = profiled(labeled, domains=("security",))
    _, paths = shown(result.listing)
    assert ("secure" in paths, "pipelines" in paths) == (True, False)


def test_a_path_matches_through_a_problem_step_and_ignores_a_step_the_catalog_lacks(
    labeled: Environment,
):
    only_data = profiled(labeled, domains=("data",)).listing
    only_algorithms = profiled(labeled, domains=("algorithms",)).listing
    assert (
        "problem-steps" in shown(only_data)[1],
        "problem-steps" in shown(only_algorithms)[1],
    ) == (False, True)


def test_a_role_profile_keeps_general_and_the_roles_it_names(labeled: Environment):
    guides, _ = shown(profiled(labeled, roles=("data-engineer",)).listing)
    assert sorted(guides) == [
        "a-loose-guide",
        "basics",
        "etl",
        "hash-functions",
        "hash-maps",
    ]


def test_hidden_counts_are_what_widen_all_would_add_with_the_same_flags(labeled: Environment):
    result = profiled(labeled, domains=("security",))
    assert (result.guides.shown, result.guides.total) == (1, 7)
    assert (result.paths.shown, result.paths.total) == (2, 4)
    assert (result.hidden_guides, result.hidden_paths) == (6, 2)


def test_a_search_narrows_the_counts_the_profile_line_gives(labeled: Environment):
    result = profiled(labeled, domains=("security",), wanted=ListingFilter(search="t"))
    everything = profiled(labeled, wanted=ListingFilter(search="t"))
    assert (result.guides.total, result.paths.total) == (
        len(everything.listing.guides),
        len(everything.listing.paths),
    )


def test_the_profile_narrows_by_the_values_it_holds_without_general(labeled: Environment):
    result = profiled(labeled, domains=("security", "data"), roles=("backend",))
    assert (result.narrowed.domains, result.narrowed.job_roles, result.narrowed.languages) == (
        ("security", "data"),
        ("backend",),
        None,
    )


def test_an_explicit_domain_replaces_the_profiles_domains(labeled: Environment):
    result = profiled(labeled, domains=("security",), domain="data")
    guides, _ = shown(result.listing)
    assert sorted(guides) == ["apis", "etl"]
    assert result.narrowed.domains is None


def test_an_explicit_domain_leaves_the_profiles_roles_applying(labeled: Environment):
    result = profiled(labeled, roles=("backend",), domain="data")
    assert shown(result.listing)[0] == ["apis"]
    assert result.narrowed.job_roles == ("backend",)


def test_an_explicit_role_matches_only_the_guides_that_list_it_not_general(labeled: Environment):
    guides, _ = shown(profiled(labeled, role="general").listing)
    assert sorted(guides) == ["a-loose-guide", "basics", "hash-functions", "hash-maps"]


def test_an_explicit_value_outside_the_profile_widens_to_it(labeled: Environment):
    guides, _ = shown(profiled(labeled, roles=("backend",), role="data-engineer").listing)
    assert guides == ["etl"]


def test_widen_domain_drops_only_the_domains_of_the_profile(labeled: Environment):
    result = profiled(labeled, domains=("security",), roles=("data-engineer",), widen=("domain",))
    assert sorted(shown(result.listing)[0]) == [
        "a-loose-guide",
        "basics",
        "etl",
        "hash-functions",
        "hash-maps",
    ]
    assert (result.narrowed.domains, result.narrowed.job_roles) == (None, ("data-engineer",))


def test_widen_all_lists_everything_and_hides_nothing(labeled: Environment):
    result = profiled(labeled, domains=("security",), roles=("backend",), widen=("all",))
    assert shown(result.listing) == shown(learn_listing(labeled))
    assert (result.hidden_guides, result.hidden_paths, result.narrowed.is_empty) == (0, 0, True)


def test_a_profile_that_narrows_but_hides_nothing_counts_zero(labeled: Environment):
    every_label = tuple(DOMAINS)
    result = profiled(labeled, domains=every_label[:-1])
    assert (result.hidden_guides, result.hidden_paths) == (0, 0)
    assert result.narrowed.domains == every_label[:-1]


def test_the_profile_applies_to_the_listing_and_not_to_a_guide_or_a_path(labeled: Environment):
    config = Config(profile=ProfileSettings(domains=("security",)))
    configured = replace(labeled, config=config)
    assert guide_page(configured, "etl").entry.meta.slug == "etl"
    assert path_view(configured, "pipelines").path.slug == "pipelines"


def test_a_workspaces_languages_do_not_narrow_guides(labeled: Environment):
    chosen = replace(labeled, workspace_languages=(Language.GO,))
    scope = label_scope(chosen)
    assert shown(profiled_listing(learn_listing(chosen), ListingFilter(), scope).listing) == shown(
        learn_listing(labeled)
    )
