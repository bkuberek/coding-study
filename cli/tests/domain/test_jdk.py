"""The JDK range cstudy supports and the range a problem declares
(docs/decisions/0016-jdk-range.md)."""

import pytest

from coding_study.domain.guides import TOOLCHAINS_GUIDE
from coding_study.domain.jdk import (
    JDK_FIX,
    SUPPORTED_JDKS,
    DeclaredJdk,
    JdkAvailability,
    JdkRange,
    JdkSource,
    SelectedJdk,
    availability,
    effective_range,
    no_jdk_sentence,
    release_level,
)


def selected(feature: int, source: JdkSource = JdkSource.JAVA_HOME) -> SelectedJdk:
    return SelectedJdk(version=f"{feature}.0.1", feature=feature, source=source)


def test_cstudy_supports_jdk_21_to_26():
    assert (SUPPORTED_JDKS.minimum, SUPPORTED_JDKS.maximum) == (21, 26)


@pytest.mark.parametrize("feature", [21, 23, 26])
def test_a_range_contains_every_release_from_its_minimum_to_its_maximum(feature):
    assert SUPPORTED_JDKS.contains(feature)


@pytest.mark.parametrize("feature", [17, 20, 27])
def test_a_range_excludes_the_releases_outside_it(feature):
    assert not SUPPORTED_JDKS.contains(feature)


# The range of a problem


def test_a_problem_without_a_jdk_declaration_runs_on_the_supported_range():
    assert effective_range(None) == SUPPORTED_JDKS


def test_a_declaration_without_bounds_is_the_supported_range():
    assert effective_range(DeclaredJdk()) == SUPPORTED_JDKS


def test_a_missing_maximum_is_the_top_of_the_supported_range():
    assert effective_range(DeclaredJdk(minimum=24)) == JdkRange(24, 26)


def test_a_missing_minimum_is_the_bottom_of_the_supported_range():
    assert effective_range(DeclaredJdk(maximum=23)) == JdkRange(21, 23)


def test_explicit_bounds_stay_where_they_are_written():
    assert effective_range(DeclaredJdk(minimum=22, maximum=25)) == JdkRange(22, 25)


def test_an_explicit_maximum_above_the_supported_range_stays_above_it():
    assert effective_range(DeclaredJdk(maximum=27)) == JdkRange(21, 27)


def test_a_missing_bound_follows_the_supported_range_when_it_grows():
    grown = JdkRange(21, 27)
    assert effective_range(DeclaredJdk(minimum=24), grown) == JdkRange(24, 27)


def test_an_explicit_bound_does_not_follow_the_supported_range_when_it_grows():
    grown = JdkRange(21, 27)
    assert effective_range(DeclaredJdk(maximum=25), grown) == JdkRange(21, 25)


# The selected JDK


@pytest.mark.parametrize("feature", [21, 26])
def test_a_selected_jdk_inside_the_supported_range_is_supported(feature):
    assert selected(feature).supported


@pytest.mark.parametrize("feature", [17, 27])
def test_a_selected_jdk_outside_the_supported_range_is_not_supported(feature):
    assert not selected(feature).supported


# Whether the selected JDK can run a problem


@pytest.mark.parametrize("feature", [21, 24, 26])
def test_a_jdk_inside_the_range_of_a_problem_runs_it(feature):
    assert availability(selected(feature), SUPPORTED_JDKS) is JdkAvailability.AVAILABLE


def test_a_problem_cannot_run_without_a_jdk():
    assert availability(None, SUPPORTED_JDKS) is JdkAvailability.NO_JDK


def test_a_jdk_below_the_supported_minimum_is_too_old():
    assert availability(selected(17), SUPPORTED_JDKS) is JdkAvailability.TOO_OLD


def test_a_jdk_below_the_minimum_a_problem_declares_is_too_old():
    wanted = effective_range(DeclaredJdk(minimum=24))
    assert availability(selected(21), wanted) is JdkAvailability.TOO_OLD


def test_a_jdk_above_the_supported_range_is_not_supported_yet():
    assert availability(selected(27), SUPPORTED_JDKS) is JdkAvailability.NOT_SUPPORTED_YET


def test_a_problem_that_opts_in_to_a_newer_jdk_runs_on_it():
    wanted = effective_range(DeclaredJdk(maximum=27))
    assert availability(selected(27), wanted) is JdkAvailability.AVAILABLE


def test_an_opt_in_does_not_reach_a_jdk_newer_than_it_names():
    wanted = effective_range(DeclaredJdk(maximum=27))
    assert availability(selected(28), wanted) is JdkAvailability.NOT_SUPPORTED_YET


def test_a_jdk_above_the_maximum_a_problem_declares_is_newer_than_the_problem_supports():
    wanted = effective_range(DeclaredJdk(maximum=23))
    assert availability(selected(25), wanted) is JdkAvailability.NEWER_THAN_THE_PROBLEM


def test_a_jdk_that_the_range_grows_to_cover_runs_a_problem_without_bounds():
    grown = JdkRange(21, 27)
    assert availability(selected(27), effective_range(None, grown)) is JdkAvailability.AVAILABLE


# When there is no JDK to run


def test_the_jdk_fix_names_the_range_and_the_recommended_jdk():
    expected = f"select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: {TOOLCHAINS_GUIDE}#jdk"
    assert expected == JDK_FIX


def test_no_jdk_found_is_said_so():
    assert no_jdk_sentence(None) == "no JDK was found"


def test_a_java_home_without_a_jdk_is_named():
    assert no_jdk_sentence("/opt/jdk") == "JAVA_HOME (/opt/jdk) holds no JDK"


# The release level of a build


@pytest.mark.parametrize("feature", [21, 24, 26])
def test_a_build_on_a_jdk_of_the_range_compiles_at_its_release(feature):
    assert release_level(feature) == feature


@pytest.mark.parametrize("feature", [27, 30])
def test_a_build_on_a_jdk_above_the_range_compiles_at_the_top_of_the_range(feature):
    assert release_level(feature) == SUPPORTED_JDKS.maximum


def test_the_top_of_the_range_is_the_cap_of_a_given_range():
    assert release_level(30, JdkRange(minimum=21, maximum=25)) == 25
