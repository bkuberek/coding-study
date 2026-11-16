"""The split of a problem's languages by what can run here: the selected JDK, and the programs
of the other languages (docs/specs/cli.md#cstudy-verify)."""

from dataclasses import replace

import pytest

from coding_study.application.toolchain_requirement import narrowed, split_by_toolchain
from coding_study.domain.problem import ALL_LANGUAGES, Language
from tests.fakes import FakeToolchainCheck, jdk_of, make_environment, without
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
NO_CARGO = "cargo was not found on PATH"
NO_NODE = "node was not found on PATH"
OUTSIDE_RANGE = "runs on JDK 21 to 26; JAVA_HOME selects JDK 27"


@pytest.fixture
def environment(content_root):
    return make_environment(content_root)


def test_every_language_runs_when_every_program_is_there(environment):
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert (split.runnable, split.skipped) == (tuple(ALL_LANGUAGES), ())


def test_a_language_without_its_program_is_skipped_with_the_reason(environment):
    environment = replace(environment, toolchain_check=without("cargo"))
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert (split.skipped, dict(split.reasons)) == ((Language.RUST,), {Language.RUST: NO_CARGO})


def test_the_other_languages_stay_runnable_in_their_order(environment):
    environment = replace(environment, toolchain_check=without("cargo", "node"))
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert split.runnable == tuple(
        language
        for language in ALL_LANGUAGES
        if language not in (Language.RUST, Language.TYPESCRIPT)
    )


def test_a_skip_follows_the_order_of_the_languages_it_was_given(environment):
    environment = replace(environment, toolchain_check=without("cargo", "node"))
    split = split_by_toolchain(
        environment, TWO_SUM, [Language.RUST, Language.GO, Language.TYPESCRIPT]
    )
    assert (split.runnable, split.skipped) == (
        (Language.GO,),
        (Language.RUST, Language.TYPESCRIPT),
    )


def test_only_the_languages_asked_for_are_checked(environment):
    environment = replace(environment, toolchain_check=without("cargo"))
    split = split_by_toolchain(environment, TWO_SUM, [Language.PYTHON])
    assert (split.runnable, split.skipped) == ((Language.PYTHON,), ())


def test_the_jdk_and_a_program_skip_together_each_with_its_own_reason(environment):
    environment = replace(environment, jdk=jdk_of(27), toolchain_check=without("cargo"))
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert dict(split.reasons) == {
        Language.JAVA: OUTSIDE_RANGE,
        Language.KOTLIN: OUTSIDE_RANGE,
        Language.RUST: NO_CARGO,
    }


def test_languages_with_one_reason_are_grouped(environment):
    environment = replace(environment, jdk=jdk_of(27), toolchain_check=without("cargo"))
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert split.reason_groups() == (
        ((Language.JAVA, Language.KOTLIN), OUTSIDE_RANGE),
        ((Language.RUST,), NO_CARGO),
    )


def test_a_check_that_names_a_missing_language_skips_it(environment):
    check = FakeToolchainCheck({Language.TYPESCRIPT: NO_NODE})
    split = split_by_toolchain(replace(environment, toolchain_check=check), TWO_SUM, ALL_LANGUAGES)
    assert split.skipped == (Language.TYPESCRIPT,)


def lang_add_reason(language: Language) -> str:
    return f"not one of this workspace's languages: cstudy lang add {language}"


def test_a_language_the_workspace_does_not_list_is_skipped_with_the_lang_add_reason(environment):
    environment = replace(environment, workspace_languages=(Language.PYTHON, Language.GO))
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert (split.runnable, dict(split.reasons)) == (
        (Language.PYTHON, Language.GO),
        {
            Language.TYPESCRIPT: lang_add_reason(Language.TYPESCRIPT),
            Language.JAVA: lang_add_reason(Language.JAVA),
            Language.KOTLIN: lang_add_reason(Language.KOTLIN),
            Language.RUST: lang_add_reason(Language.RUST),
        },
    )


def test_an_unlisted_language_keeps_its_place_among_the_skipped(environment):
    environment = replace(environment, workspace_languages=(Language.GO,))
    split = split_by_toolchain(environment, TWO_SUM, [Language.RUST, Language.GO, Language.PYTHON])
    assert (split.runnable, split.skipped) == ((Language.GO,), (Language.RUST, Language.PYTHON))


def test_a_workspace_that_chose_no_languages_skips_none_for_that_reason(environment):
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert dict(split.reasons) == {}


def test_the_workspace_reason_takes_a_language_the_jdk_would_skip_too(environment):
    environment = replace(
        environment, jdk=jdk_of(27), workspace_languages=(Language.PYTHON, Language.JAVA)
    )
    split = split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES)
    assert (split.reasons[Language.KOTLIN], split.reasons[Language.JAVA]) == (
        lang_add_reason(Language.KOTLIN),
        OUTSIDE_RANGE,
    )


def test_a_listed_language_without_its_program_is_skipped_for_the_program(environment):
    environment = replace(
        environment,
        toolchain_check=without("cargo"),
        workspace_languages=(Language.PYTHON, Language.RUST),
    )
    assert (
        dict(split_by_toolchain(environment, TWO_SUM, ALL_LANGUAGES).reasons)[Language.RUST]
        == NO_CARGO
    )


def test_languages_with_one_unlisted_reason_stay_one_group_each(environment):
    environment = replace(environment, workspace_languages=(Language.PYTHON,))
    groups = split_by_toolchain(environment, TWO_SUM, [Language.GO, Language.RUST]).reason_groups()
    assert groups == (
        ((Language.GO,), lang_add_reason(Language.GO)),
        ((Language.RUST,), lang_add_reason(Language.RUST)),
    )


def test_narrowed_keeps_the_order_and_drops_what_is_skipped():
    assert narrowed(ALL_LANGUAGES, None, (Language.GO, Language.RUST)) == [
        language for language in ALL_LANGUAGES if language not in (Language.GO, Language.RUST)
    ]


def test_narrowed_to_one_language():
    assert narrowed(ALL_LANGUAGES, Language.GO, (Language.RUST,)) == [Language.GO]
