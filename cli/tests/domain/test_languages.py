from coding_study.domain.problem import (
    ALL_LANGUAGES,
    CORE_LANGUAGES,
    LANGUAGE_SUBSET_TRACKS,
    Language,
    Track,
)


def test_every_problem_lists_all_six_languages_by_default():
    assert tuple(Language) == ALL_LANGUAGES


def test_core_languages_are_the_toolchains_every_workspace_needs():
    assert CORE_LANGUAGES == (
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.JAVA,
        Language.KOTLIN,
    )


def test_only_concurrency_and_debugging_problems_list_a_subset():
    assert {Track.CONCURRENCY, Track.DEBUGGING} == LANGUAGE_SUBSET_TRACKS
