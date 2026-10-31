"""Project problems (docs/specs/problem-format.md#project-problems): a folder of seeded files in
one language, graded through an entry class and opened in levels as progressive problems are.

The `project` block of meta.yaml names the entry and the directory that receives the native test
files `cstudy` generates per level. Paths inside a project folder are relative and `/`-separated,
and none may lead out of the folder.
"""

import keyword
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from coding_study.domain.problem import Language

DEFAULT_TESTS_DIRECTORY = "tests"
PATH_SEPARATOR = "/"
_PARENT_SEGMENT = ".."
_CURRENT_SEGMENT = "."
_WINDOWS_SEPARATOR = "\\"
_PYTHON_SOURCE_SUFFIX = ".py"
_PYTHON_PACKAGE_FILE = "__init__.py"
_TYPESCRIPT_SOURCE_SUFFIX = ".ts"


@dataclass(frozen=True, slots=True)
class Project:
    """The `project` block of meta.yaml."""

    entry: str
    """Where the entry class lives: a dotted module in Python (`bank.bank`), a file relative to the
    project root in TypeScript (`src/bank.ts`)."""
    tests: str = DEFAULT_TESTS_DIRECTORY
    """The directory, relative to the project root, that receives the generated level tests."""


def relative_path_issue(path: str) -> str | None:
    """Why `path` cannot name a file or directory inside a folder; None when it can.

    A valid path is relative, `/`-separated and canonical: no `..` that could leave the folder,
    and no empty or `.` segment, so that equal paths are equal strings.
    """
    if not path:
        return "is empty"
    if path.startswith(PATH_SEPARATOR):
        return "is absolute"
    if _WINDOWS_SEPARATOR in path:
        return f"uses {_WINDOWS_SEPARATOR} instead of {PATH_SEPARATOR}"
    segments = path.split(PATH_SEPARATOR)
    if _PARENT_SEGMENT in segments:
        return f'leaves its folder through "{_PARENT_SEGMENT}"'
    if any(segment in ("", _CURRENT_SEGMENT) for segment in segments):
        return f'has an empty or "{_CURRENT_SEGMENT}" segment'
    return None


def entry_issue(entry: str, language: Language) -> str | None:
    """Why `entry` cannot name the entry of a project in `language`; None when it can.

    Raises ValueError for a language without project problems.
    """
    return _project_language(language).entry_issue(entry)


def entry_files(entry: str, language: Language) -> tuple[str, ...]:
    """The project files, any one of which defines a well-formed `entry`.

    Raises ValueError for a language without project problems.
    """
    return _project_language(language).entry_files(entry)


def level_test_file(project: Project, language: Language, level: int) -> str:
    """The generated test file of `level`, relative to the project root.

    Raises ValueError for a language without project problems.
    """
    name = _project_language(language).level_test_name.format(level=level)
    return f"{project.tests}{PATH_SEPARATOR}{name}"


@dataclass(frozen=True, slots=True)
class _ProjectLanguage:
    entry_issue: Callable[[str], str | None]
    entry_files: Callable[[str], tuple[str, ...]]
    level_test_name: str
    """A format string with a `level` field."""


def _python_entry_issue(entry: str) -> str | None:
    modules = entry.split(".")
    if all(module.isidentifier() and not keyword.iskeyword(module) for module in modules):
        return None
    return f'"{entry}" is not a dotted module name such as bank.bank'


def _python_entry_files(entry: str) -> tuple[str, ...]:
    """A module file, or the `__init__.py` of a package."""
    module = entry.replace(".", PATH_SEPARATOR)
    return (
        f"{module}{_PYTHON_SOURCE_SUFFIX}",
        f"{module}{PATH_SEPARATOR}{_PYTHON_PACKAGE_FILE}",
    )


def _typescript_entry_issue(entry: str) -> str | None:
    if entry.endswith(_TYPESCRIPT_SOURCE_SUFFIX) and relative_path_issue(entry) is None:
        return None
    return f'"{entry}" is not a .ts file inside the project such as src/bank.ts'


_PROJECT_LANGUAGES: Mapping[Language, _ProjectLanguage | None] = {
    Language.PYTHON: _ProjectLanguage(
        _python_entry_issue, _python_entry_files, "test_level_{level}.py"
    ),
    Language.TYPESCRIPT: _ProjectLanguage(
        _typescript_entry_issue, lambda entry: (entry,), "level-{level}.test.ts"
    ),
    Language.JAVA: None,
    Language.KOTLIN: None,
    Language.GO: None,
    Language.RUST: None,
}
"""None: not yet supported; Java, Kotlin, Go and Rust wait for spikes (ADR 0014)."""
PROJECT_LANGUAGES = tuple(language for language, found in _PROJECT_LANGUAGES.items() if found)
"""The languages a project problem may list."""


def unsupported_language(language: Language) -> str:
    return f"project problems are not yet supported in {language}"


def _project_language(language: Language) -> _ProjectLanguage:
    found = _PROJECT_LANGUAGES[language]
    if found is None:
        raise ValueError(unsupported_language(language))
    return found
