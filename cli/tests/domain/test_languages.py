from coding_study.domain.problem import CORE_LANGUAGES, OPTIONAL_LANGUAGES, Language


def test_core_languages_are_the_four_every_problem_lists():
    assert CORE_LANGUAGES == (
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.JAVA,
        Language.KOTLIN,
    )


def test_optional_languages_are_go_and_rust():
    assert OPTIONAL_LANGUAGES == (Language.GO, Language.RUST)


def test_core_and_optional_languages_partition_the_enum():
    assert (*CORE_LANGUAGES, *OPTIONAL_LANGUAGES) == tuple(Language)
