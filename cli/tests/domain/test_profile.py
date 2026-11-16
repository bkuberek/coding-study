"""The learner profile's rule (docs/specs/cli.md#matching, #explicit-filters-and-widening and
#the-profile-line)."""

import pytest

from coding_study.domain.config import ProfileSettings
from coding_study.domain.labels import Labels
from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.domain.profile import (
    ALL_DIMENSIONS,
    GUIDE_DIMENSIONS,
    PICK_DIMENSIONS,
    Counted,
    Dimension,
    NarrowedValues,
    Profile,
    ProfileLineKind,
    Widening,
    learner_profile,
    profile_line,
    widening_from,
)
from coding_study.domain.taxonomy import DOMAINS, PROFILE_JOB_ROLES

PY_GO = (Language.PYTHON, Language.GO)
NO_LANGUAGES = ()


def labels(domains: tuple[str, ...] = (), job_roles: tuple[str, ...] = ()) -> Labels:
    return Labels(domains=domains, job_roles=job_roles)


BACKEND = Profile(job_roles=("backend",))
SECURITY = Profile(domains=("security",))
PYTHON_GO = Profile(languages=PY_GO, languages_chosen=True)


def test_a_profile_that_holds_every_value_narrows_nothing():
    assert [Profile().narrows(dimension) for dimension in Dimension] == [False, False, False]


def test_a_dimension_narrows_when_it_holds_fewer_than_all_its_values():
    profile = Profile(languages=PY_GO, job_roles=("backend",), domains=("security", "data"))
    assert [profile.narrows(dimension) for dimension in Dimension] == [True, True, True]


def test_a_list_that_names_every_value_does_not_narrow_whatever_its_order():
    profile = Profile(
        job_roles=tuple(reversed(PROFILE_JOB_ROLES)), domains=tuple(reversed(DOMAINS))
    )
    assert not profile.narrows(Dimension.JOB_ROLES)
    assert not profile.narrows(Dimension.DOMAINS)


def test_a_profile_that_narrows_nothing_keeps_every_entry():
    entry = labels(("security",), ("security-engineer",))
    assert Profile().matches(entry, (Language.RUST,))


@pytest.mark.parametrize(
    ("entry_roles", "kept"),
    [
        (("backend",), True),
        (("platform", "backend"), True),
        (("platform",), False),
        (("general",), True),
        (("general", "platform"), True),
        ((), True),
    ],
    ids=["listed", "one of several", "other role", "general", "general and other", "no role"],
)
def test_a_role_profile_keeps_general_and_entries_without_roles(entry_roles, kept):
    assert BACKEND.matches(labels(job_roles=entry_roles)) is kept


@pytest.mark.parametrize(
    ("entry_domains", "kept"),
    [
        (("security",), True),
        (("backend", "security"), True),
        (("backend",), False),
        ((), True),
    ],
    ids=["listed", "one of several", "other domain", "no domain"],
)
def test_a_domain_profile_keeps_entries_that_list_one_of_its_domains_or_none(entry_domains, kept):
    assert SECURITY.matches(labels(domains=entry_domains)) is kept


@pytest.mark.parametrize(
    ("entry_languages", "kept"),
    [
        ((Language.PYTHON, Language.JAVA), True),
        ((Language.GO,), True),
        ((Language.JAVA, Language.KOTLIN), False),
        (NO_LANGUAGES, True),
    ],
    ids=["one of several", "listed", "other languages", "rubric problem"],
)
def test_a_language_profile_keeps_a_rubric_problem(entry_languages, kept):
    assert PYTHON_GO.matches(labels(), entry_languages) is kept


def test_every_applied_dimension_must_match():
    profile = Profile(languages=PY_GO, job_roles=("backend",), domains=("security",))
    entry = labels(("security",), ("backend",))
    assert profile.matches(entry, (Language.GO,))
    assert not profile.matches(labels(("data",), ("backend",)), (Language.GO,))
    assert not profile.matches(entry, (Language.RUST,))
    assert not profile.matches(labels(("security",), ("platform",)), (Language.GO,))


def test_a_dimension_the_command_does_not_apply_matches_whatever_the_entry_holds():
    profile = Profile(languages=PY_GO, domains=("security",))
    assert profile.matches(labels(("security",)), (Language.RUST,), applies=GUIDE_DIMENSIONS)
    assert not profile.matches(labels(("data",)), (Language.GO,), applies=GUIDE_DIMENSIONS)


@pytest.mark.parametrize(
    ("widening", "kept"),
    [
        (Widening(), False),
        (Widening(frozenset({Dimension.LANGUAGES})), False),
        (Widening(frozenset({Dimension.DOMAINS})), True),
        (Widening(frozenset(Dimension)), True),
    ],
    ids=["none", "other dimension", "its dimension", "all"],
)
def test_a_widened_dimension_drops_the_profile_there(widening, kept):
    profile = Profile(domains=("security",))
    assert profile.matches(labels(("data",)), widening=widening) is kept


def test_widening_one_dimension_keeps_the_others_narrowing():
    profile = Profile(job_roles=("backend",), domains=("security",))
    widening = Widening().plus(Dimension.DOMAINS)
    assert profile.matches(labels(("data",), ("backend",)), widening=widening)
    assert not profile.matches(labels(("data",), ("platform",)), widening=widening)


@pytest.mark.parametrize(
    ("values", "dimensions"),
    [
        ([], set()),
        (["lang"], {Dimension.LANGUAGES}),
        (["role", "domain"], {Dimension.JOB_ROLES, Dimension.DOMAINS}),
        (["domain", "domain"], {Dimension.DOMAINS}),
        (["all"], set(ALL_DIMENSIONS)),
        (["role", "all"], set(ALL_DIMENSIONS)),
    ],
)
def test_widen_values_name_one_dimension_or_all_three(values, dimensions):
    assert widening_from(values).dimensions == dimensions


def test_an_unknown_widen_value_is_refused():
    with pytest.raises(ValueError, match='unknown widening "everything"'):
        widening_from(["everything"])


@pytest.mark.parametrize(
    ("values", "dimensions"),
    [
        (["role"], {Dimension.JOB_ROLES}),
        (["role", "domain"], {Dimension.JOB_ROLES, Dimension.DOMAINS}),
        (["all"], set(ALL_DIMENSIONS)),
    ],
)
def test_picks_take_role_domain_and_all(values, dimensions):
    assert widening_from(values, PICK_DIMENSIONS).dimensions == dimensions


def test_picks_refuse_lang_and_name_what_they_take():
    with pytest.raises(ValueError, match='unknown widening "lang"; use role, domain or all'):
        widening_from(["lang"], PICK_DIMENSIONS)


def test_the_widen_values_of_list_name_the_three_dimensions():
    with pytest.raises(ValueError, match="use lang, role, domain or all"):
        widening_from(["nothing"])


def test_narrowed_values_are_those_of_the_dimensions_that_narrowed_this_run():
    profile = Profile(languages=PY_GO, job_roles=("backend",), domains=DOMAINS)
    assert profile.narrowed() == NarrowedValues(languages=("python", "go"), job_roles=("backend",))


def test_narrowed_values_leave_out_a_widened_dimension_and_one_the_command_does_not_apply():
    profile = Profile(languages=PY_GO, job_roles=("backend",), domains=("security",))
    narrowed = profile.narrowed(GUIDE_DIMENSIONS, Widening().plus(Dimension.JOB_ROLES))
    assert narrowed == NarrowedValues(domains=("security",))


def test_a_profile_that_narrows_nothing_has_empty_narrowed_values():
    assert Profile().narrowed().is_empty


def test_the_profile_of_a_config_and_unchosen_languages_holds_all_six():
    profile = learner_profile(ProfileSettings(domains=("data",)))
    assert profile == Profile(domains=("data",), languages=ALL_LANGUAGES, languages_chosen=False)


def test_the_profile_of_chosen_languages_lists_them_in_language_order():
    profile = learner_profile(ProfileSettings(), (Language.GO, Language.PYTHON))
    assert (profile.languages, profile.languages_chosen) == (PY_GO, True)


def test_a_workspace_that_chose_all_six_languages_narrows_nothing_but_is_chosen():
    profile = learner_profile(ProfileSettings(), tuple(reversed(ALL_LANGUAGES)))
    assert (profile.languages, profile.languages_chosen) == (ALL_LANGUAGES, True)
    assert not profile.narrows(Dimension.LANGUAGES)


LIST_NARROWED = NarrowedValues(languages=("python", "go"))


def test_the_list_line_counts_the_rows_and_names_the_widening():
    line = profile_line(ProfileLineKind.SHOWS, [Counted(120, 400, "problems")], LIST_NARROWED)
    assert line == (
        "filtered by your profile: 120 of 400 problems · languages python, go · "
        "--widen all shows all 400"
    )


def test_the_line_names_every_narrowed_dimension_in_order_with_general_after_the_roles():
    narrowed = NarrowedValues(
        languages=("python", "go"), job_roles=("backend",), domains=("security", "data")
    )
    line = profile_line(ProfileLineKind.SHOWS, [Counted(120, 400, "problems")], narrowed)
    assert line == (
        "filtered by your profile: 120 of 400 problems · languages python, go · "
        "roles backend and general · domains security, data · --widen all shows all 400"
    )


def test_the_next_line_says_picked_from_and_picks_from_all():
    line = profile_line(
        ProfileLineKind.PICKS,
        [Counted(120, 400, "problems")],
        NarrowedValues(job_roles=("backend",)),
    )
    assert line == (
        "filtered by your profile: picked from 120 of 400 problems · roles backend and general · "
        "--widen all picks from all 400"
    )


def test_the_mock_line_names_the_scope_of_the_picks():
    line = profile_line(
        ProfileLineKind.PICKS,
        [Counted(30, 95, "new medium and hard problems")],
        NarrowedValues(domains=("security",)),
    )
    assert line == (
        "filtered by your profile: picked from 30 of 95 new medium and hard problems · "
        "domains security · --widen all picks from all 95"
    )


def test_the_learn_line_counts_guides_and_paths():
    line = profile_line(
        ProfileLineKind.SHOWS_THEM,
        [Counted(40, 132, "guides"), Counted(9, 20, "paths")],
        NarrowedValues(domains=("security",)),
    )
    assert line == (
        "filtered by your profile: 40 of 132 guides, 9 of 20 paths · domains security · "
        "--widen all shows them all"
    )


def test_no_line_while_the_profile_hid_nothing():
    assert (
        profile_line(ProfileLineKind.SHOWS, [Counted(400, 400, "problems")], LIST_NARROWED) is None
    )
    assert (
        profile_line(
            ProfileLineKind.SHOWS_THEM,
            [Counted(132, 132, "guides"), Counted(20, 20, "paths")],
            NarrowedValues(domains=("security",)),
        )
        is None
    )


def test_the_learn_line_shows_while_only_the_paths_were_hidden():
    line = profile_line(
        ProfileLineKind.SHOWS_THEM,
        [Counted(132, 132, "guides"), Counted(9, 20, "paths")],
        NarrowedValues(domains=("security",)),
    )
    assert line is not None
    assert "132 of 132 guides, 9 of 20 paths" in line
