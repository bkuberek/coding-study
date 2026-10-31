"""Project problems (docs/specs/problem-format.md#project-problems): a folder of seeded files in
one language, graded through an entry class and opened in levels as progressive problems are.

The `project` block of meta.yaml names the entry and the directory that receives the native test
files `cstudy` generates per level. `starter/` and each approach's `solutions/<approach>/`, an
overlay of changed and added files on the starter, are trees of plain files. Paths inside a project
folder are relative and `/`-separated, and none may lead out of the folder.
"""

import keyword
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

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


@dataclass(frozen=True, slots=True)
class ProjectFile:
    path: str
    """Relative to its folder, as `relative_path_issue` requires."""
    size: int
    """In bytes."""
    text: str | None
    """The content, when it is UTF-8 without NUL bytes; None otherwise."""

    def __post_init__(self) -> None:
        issue = relative_path_issue(self.path)
        if issue is not None:
            raise ValueError(f'project file "{self.path}" {issue}')


@dataclass(frozen=True, slots=True)
class ProjectTree:
    """The plain files of one folder, in path order."""

    files: tuple[ProjectFile, ...]

    @property
    def paths(self) -> frozenset[str]:
        return frozenset(file.path for file in self.files)

    @property
    def size(self) -> int:
        return sum(file.size for file in self.files)

    def file(self, path: str) -> ProjectFile | None:
        return next((file for file in self.files if file.path == path), None)


@dataclass(frozen=True, slots=True)
class ProjectFiles:
    """The trees in a project problem's directory."""

    starter: ProjectTree | None
    """`starter/`, or None when the problem has none."""
    overlays: Mapping[str, ProjectTree] = field(default_factory=dict[str, ProjectTree])
    """Every directory in `solutions/` by name: the reference of the approach it names, as the
    files it changes or adds on the starter."""


NO_PROJECT_FILES = ProjectFiles(None)
"""What a problem without trees has: no starter and no overlays."""


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
    names = _project_language(language)
    name = f"{names.level_test_prefix}{level}{names.level_test_suffix}"
    return f"{project.tests}{PATH_SEPARATOR}{name}"


def level_test_pattern(language: Language) -> re.Pattern[str]:
    """Matches the file name of a generated test file of any level.

    Raises ValueError for a language without project problems.
    """
    names = _project_language(language)
    prefix, suffix = re.escape(names.level_test_prefix), re.escape(names.level_test_suffix)
    return re.compile(f"{prefix}[1-9][0-9]*{suffix}")


@dataclass(frozen=True, slots=True)
class _ProjectLanguage:
    entry_issue: Callable[[str], str | None]
    entry_files: Callable[[str], tuple[str, ...]]
    level_test_prefix: str
    level_test_suffix: str
    """A generated test file is named prefix, level number, suffix."""


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
        _python_entry_issue, _python_entry_files, "test_level_", ".py"
    ),
    Language.TYPESCRIPT: _ProjectLanguage(
        _typescript_entry_issue, lambda entry: (entry,), "level-", ".test.ts"
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
