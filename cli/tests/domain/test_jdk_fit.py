"""Whether the selected JDK can run a problem's Java and Kotlin, and the words for when it cannot
(docs/specs/cli.md#the-selected-jdk)."""

from dataclasses import replace

import pytest

from coding_study.domain.jdk import DeclaredJdk, JdkRange, JdkSource, SelectedJdk
from coding_study.domain.jdk_fit import JdkFit, content_release, fit_of, range_text
from coding_study.domain.problem import Language, ProblemMeta
from tests.stub_contract import STUB_CASES

PROBLEM = "two-sum"
TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")


def selected(feature: int, source: JdkSource = JdkSource.JAVA_HOME) -> SelectedJdk:
    return SelectedJdk(version=f"{feature}.0.1", feature=feature, source=source)


def meta_with(declared: DeclaredJdk | None) -> ProblemMeta:
    return replace(TWO_SUM, jdk=declared)


def fit(
    jdk: SelectedJdk | None,
    declared: DeclaredJdk | None = None,
    java_home: str | None = None,
) -> JdkFit:
    return fit_of(jdk, java_home, declared)


@pytest.mark.parametrize(
    ("wanted", "text"),
    [
        (JdkRange(21, 26), "JDK 21 to 26"),
        (JdkRange(24, 26), "JDK 24 to 26"),
        (JdkRange(24, 24), "JDK 24"),
    ],
)
def test_a_range_reads_as_its_bounds(wanted, text):
    assert range_text(wanted) == text


@pytest.mark.parametrize("feature", [21, 24, 26])
def test_a_jdk_in_the_default_range_runs_a_problem_that_declares_nothing(feature):
    assert fit(selected(feature)).runs


@pytest.mark.parametrize("jdk", [None, selected(17), selected(27)], ids=["none", "17", "27"])
def test_a_jdk_outside_the_default_range_runs_nothing(jdk):
    assert not fit(jdk).runs


def test_a_jdk_below_the_declared_minimum_does_not_run_the_problem():
    assert not fit(selected(23), DeclaredJdk(minimum=24)).runs


def test_a_jdk_above_the_declared_maximum_does_not_run_the_problem():
    assert not fit(selected(25), DeclaredJdk(maximum=24)).runs


def test_a_problem_that_declares_a_maximum_above_the_range_runs_on_that_jdk():
    assert fit(selected(27), DeclaredJdk(maximum=27)).runs


# The refusal of `start`, `test`, `submit` and `bench`


def test_a_jdk_above_the_supported_range_is_not_supported_yet():
    assert fit(selected(27)).refusal(PROBLEM, Language.JAVA) == (
        "two-sum runs its java version on JDK 21 to 26; "
        "JAVA_HOME selects JDK 27, which cstudy does not support yet"
    )


def test_a_jdk_below_the_declared_minimum_is_too_old():
    refusal = fit(selected(23), DeclaredJdk(minimum=24)).refusal(PROBLEM, Language.KOTLIN)
    assert refusal == (
        "two-sum runs its kotlin version on JDK 24 to 26; JAVA_HOME selects JDK 23, "
        "which is too old"
    )


def test_a_jdk_below_the_supported_range_is_too_old():
    assert (
        fit(selected(17))
        .refusal(PROBLEM, Language.JAVA)
        .endswith("JAVA_HOME selects JDK 17, which is too old")
    )


def test_a_jdk_above_the_declared_maximum_is_newer_than_the_problem_supports():
    refusal = fit(selected(25, JdkSource.PATH), DeclaredJdk(maximum=24)).refusal(
        PROBLEM, Language.JAVA
    )
    assert refusal == (
        "two-sum runs its java version on JDK 21 to 24; PATH selects JDK 25, "
        "which is newer than the problem supports"
    )


def test_a_jdk_above_a_declared_range_that_reaches_the_top_is_not_supported_yet():
    refusal = fit(selected(27), DeclaredJdk(minimum=24)).refusal(PROBLEM, Language.JAVA)
    assert refusal.endswith("JAVA_HOME selects JDK 27, which cstudy does not support yet")


def test_no_jdk_at_all_is_said_instead_of_a_selection():
    assert fit(None).refusal(PROBLEM, Language.JAVA) == (
        "two-sum runs its java version on JDK 21 to 26; no JDK was found"
    )


def test_a_java_home_without_a_jdk_names_the_directory():
    refusal = fit(None, java_home="/opt/jdk").refusal(PROBLEM, Language.JAVA)
    assert refusal == (
        "two-sum runs its java version on JDK 21 to 26; JAVA_HOME (/opt/jdk) holds no JDK"
    )


# The line of `verify` that skips a problem's Java and Kotlin


def test_verify_names_the_range_and_the_jdk_it_skips_for():
    reason = fit(selected(21), DeclaredJdk(minimum=24)).skip_reason()
    assert reason == "runs on JDK 24 to 26; JAVA_HOME selects JDK 21"


def test_verify_names_a_missing_jdk():
    assert fit(None).skip_reason() == "runs on JDK 21 to 26; no JDK was found"


# The release level of content builds


def test_content_compiles_at_the_declared_minimum():
    assert content_release(meta_with(DeclaredJdk(minimum=24))) == 24


@pytest.mark.parametrize("declared", [None, DeclaredJdk(maximum=23)], ids=["none", "max only"])
def test_content_compiles_at_the_supported_minimum_without_a_declared_one(declared):
    assert content_release(meta_with(declared)) == 21
