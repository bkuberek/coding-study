"""A workspace's languages and the template files each one owns
(docs/specs/installation-and-workspaces.md#workspace-languages)."""

from collections.abc import Iterable, Mapping
from typing import assert_never, cast

from coding_study.domain.problem import ALL_LANGUAGES, Language

LANGUAGE_CHOICES = "python, typescript, java, kotlin, go or rust"
"""The values a language option takes, in the order a workspace lists them."""


class WorkspaceLanguageError(ValueError):
    """A language value that no workspace can have; the text is what the command prints."""


def template_paths(language: Language) -> tuple[str, ...]:
    """The template paths, top-level folders and files, that `language` needs in a workspace.
    Java and Kotlin share `jvm/`: one Gradle build holds both subprojects."""
    match language:
        case Language.PYTHON:
            return ("python",)
        case Language.TYPESCRIPT:
            return ("typescript",)
        case Language.JAVA | Language.KOTLIN:
            return ("jvm",)
        case Language.GO:
            return ("go", "go.work")
        case Language.RUST:
            return ("rust",)
        case _ as unreachable:
            assert_never(unreachable)


TEMPLATE_PATHS: Mapping[Language, tuple[str, ...]] = {
    language: template_paths(language) for language in ALL_LANGUAGES
}


FILE_PATHS = frozenset({"go.work"})
"""The template paths that are files; every other one is a folder."""


def parse_language(text: str) -> Language:
    """Raises WorkspaceLanguageError for anything but one of the six language names."""
    try:
        return Language(text)
    except ValueError:
        raise WorkspaceLanguageError(f'unknown language "{text}"; use {LANGUAGE_CHOICES}') from None


def ordered(languages: Iterable[Language]) -> tuple[Language, ...]:
    """Each language once, in the order a workspace lists them."""
    chosen = set(languages)
    return tuple(language for language in ALL_LANGUAGES if language in chosen)


def choose(values: Iterable[str]) -> tuple[Language, ...]:
    """The languages named by `values`, such as the repeated `--lang`, each once and in the
    order a workspace lists them. Raises WorkspaceLanguageError for an unknown name."""
    return ordered(parse_language(value) for value in values)


def from_marker(value: object) -> tuple[Language, ...]:
    """The languages of a marker's `languages` value. Raises WorkspaceLanguageError for a value
    that is not a list, an empty list, an unknown name or a name listed twice."""
    if not isinstance(value, list):
        raise WorkspaceLanguageError(f"not a list; use {LANGUAGE_CHOICES}")
    names = [str(item) for item in cast(list[object], value)]
    if not names:
        raise WorkspaceLanguageError(f"empty; list at least one of {LANGUAGE_CHOICES}")
    languages = [parse_language(name) for name in names]
    for language in languages:
        if languages.count(language) > 1:
            raise WorkspaceLanguageError(f"{language.value} is listed twice; list each once")
    return ordered(languages)


def template_includes(languages: Iterable[Language] | None, relative_path: str) -> bool:
    """Whether the workspace's `languages` own the template file `relative_path`: a file of
    another language's folder is left out, and a shared file always comes. None, a marker
    without `languages`, is every language."""
    if languages is None:
        return True
    top = relative_path.partition("/")[0]
    if not any(top in paths for paths in TEMPLATE_PATHS.values()):
        return True
    return any(top in TEMPLATE_PATHS[language] for language in languages)


def owns_template(languages: Iterable[Language], relative_path: str) -> bool:
    """Whether `relative_path` is a template file of one of `languages`: a shared file
    (`README.md`, `notes/`) belongs to none of them."""
    top = relative_path.partition("/")[0]
    return any(top in TEMPLATE_PATHS[language] for language in languages)


def folder_groups(languages: Iterable[Language]) -> tuple[tuple[str, ...], ...]:
    """The template paths of `languages`, grouped as the languages share them: Java and Kotlin
    give `jvm` once, Go gives `go` and `go.work` together. In workspace order."""
    groups: list[tuple[str, ...]] = []
    for language in ordered(languages):
        if TEMPLATE_PATHS[language] not in groups:
            groups.append(TEMPLATE_PATHS[language])
    return tuple(groups)


def sharing(paths: tuple[str, ...]) -> tuple[Language, ...]:
    """The languages whose template is exactly `paths`: Java and Kotlin for `jvm`."""
    return tuple(language for language in ALL_LANGUAGES if TEMPLATE_PATHS[language] == paths)


def folder_text(paths: Iterable[str]) -> str:
    """The paths as the output names them: `go/ and go.work`, `python/, go/ and go.work`."""
    names = [path if path in FILE_PATHS else f"{path}/" for path in paths]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
