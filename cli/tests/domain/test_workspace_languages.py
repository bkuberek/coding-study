"""A workspace's languages (docs/specs/installation-and-workspaces.md#workspace-languages)."""

import pytest

from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.domain.workspace_languages import (
    TEMPLATE_PATHS,
    WorkspaceLanguageError,
    choose,
    from_marker,
    ordered,
    parse_language,
    template_includes,
    template_paths,
)

UNKNOWN = 'unknown language "golang"; use python, typescript, java, kotlin, go or rust'


@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_every_language_has_template_paths(language):
    assert TEMPLATE_PATHS[language] == template_paths(language) != ()


@pytest.mark.parametrize(
    ("language", "paths"),
    [
        (Language.PYTHON, ("python",)),
        (Language.TYPESCRIPT, ("typescript",)),
        (Language.JAVA, ("jvm",)),
        (Language.KOTLIN, ("jvm",)),
        (Language.GO, ("go", "go.work")),
        (Language.RUST, ("rust",)),
    ],
)
def test_a_language_owns_its_folders(language, paths):
    assert template_paths(language) == paths


def test_a_language_parses_from_its_name():
    assert parse_language("kotlin") is Language.KOTLIN


def test_an_unknown_name_says_what_to_use():
    with pytest.raises(WorkspaceLanguageError, match=UNKNOWN):
        parse_language("golang")


def test_a_name_in_capitals_is_unknown():
    with pytest.raises(WorkspaceLanguageError, match="unknown language"):
        parse_language("Python")


def test_languages_come_in_workspace_order_each_once():
    assert choose(["rust", "go", "python", "go"]) == (Language.PYTHON, Language.GO, Language.RUST)


def test_choosing_an_unknown_name_fails_whatever_its_place():
    with pytest.raises(WorkspaceLanguageError, match=UNKNOWN):
        choose(["python", "golang"])


def test_ordering_keeps_each_language_once():
    assert ordered([Language.KOTLIN, Language.JAVA, Language.KOTLIN]) == (
        Language.JAVA,
        Language.KOTLIN,
    )


def test_a_marker_lists_languages():
    assert from_marker(["go", "python"]) == (Language.PYTHON, Language.GO)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (["python", "golang"], UNKNOWN),
        ([], "empty"),
        ("python", "not a list"),
        (3, "not a list"),
        (["python", "python"], "python is listed twice"),
        ([3], 'unknown language "3"'),
    ],
)
def test_a_marker_refuses_what_no_workspace_has(value, message):
    with pytest.raises(WorkspaceLanguageError, match=message):
        from_marker(value)


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("python/pyproject.toml", True),
        ("typescript/package.json", False),
        ("jvm/gradlew", False),
        ("go/go.mod", False),
        ("go.work", False),
        ("rust/Cargo.toml", False),
        ("notes/.gitkeep", True),
        ("problems/.gitkeep", True),
        ("projects/.gitkeep", True),
        ("README.md", True),
        (".gitignore", True),
    ],
)
def test_python_alone_has_its_folder_and_the_shared_files(relative, expected):
    assert template_includes((Language.PYTHON,), relative) is expected


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_either_jvm_language_has_the_whole_jvm_folder(language):
    assert template_includes((language,), "jvm/kotlin/build.gradle.kts") is True


def test_go_has_its_folder_and_go_work():
    paths = ("go/go.mod", "go.work", "python/pyproject.toml")
    assert [template_includes((Language.GO,), path) for path in paths] == [True, True, False]


def test_no_chosen_languages_means_every_file():
    assert all(template_includes(None, path) for path in ("rust/lib.rs", "go.work", "jvm/gradlew"))
