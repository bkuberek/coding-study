"""An attempt's files, as the web UI's file tree and editor show them
(docs/specs/web-ui.md#file-api-rules).

Each attempt has a root and a scope: a project its folder, a single-file problem on the JVM or in
Go its package directory, any other problem the directory of its file, an item its track's notes
directory. Paths are relative to the root; none may leave it, and no link on the way is followed.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import assert_never

from coding_study.application.environment import Environment
from coding_study.application.project_manifest import folder_states
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UnknownFileError, UsageError
from coding_study.domain.file_states import FileState
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, Problem, ProblemKind
from coding_study.domain.project import PATH_SEPARATOR
from coding_study.domain.project_manifest import FileOrigin, folder_path
from coding_study.domain.workspace_projects import is_untracked, project_folder

EDITABLE_BYTES = 1024 * 1024
"""UTF-8 text up to 1 MiB opens in an editor; any other file opens read-only."""
TOOL_OUTPUT = "the page never shows what tools write (.venv, node_modules, caches, build output)"


class StartedFile(StrEnum):
    """The file `cstudy start` wrote for a single-file problem or an item."""

    STUB = "stub"
    NOTES = "notes"


@dataclass(frozen=True, slots=True)
class ScopedFile:
    path: str
    """Relative to the attempt's root, `/`-separated."""
    origin: FileOrigin | StartedFile
    level: int | None = None
    """A project's generated test file: its level."""
    state: FileState | None = None
    """A project file against what `cstudy` provided; None for other attempts."""


@dataclass(frozen=True, slots=True)
class TreeFile:
    file: ScopedFile
    size: int | None
    """None for a file the folder lacks, such as a deleted starter file."""
    editable: bool

    @property
    def path(self) -> str:
        return self.file.path

    @property
    def origin(self) -> FileOrigin | StartedFile:
        return self.file.origin

    @property
    def level(self) -> int | None:
        return self.file.level

    @property
    def state(self) -> FileState | None:
        return self.file.state


@dataclass(frozen=True, slots=True)
class AttemptTree:
    root: str
    """Relative to the workspace root."""
    files: tuple[TreeFile, ...]
    """The scope's files in path order."""


@dataclass(frozen=True, slots=True)
class FileContent:
    file: ScopedFile
    content: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    @property
    def text(self) -> str | None:
        """None for a file over `EDITABLE_BYTES` or not UTF-8."""
        return _text(self.content)

    @property
    def editable(self) -> bool:
        return self.text is not None


@dataclass(frozen=True, slots=True)
class _Scope:
    root: str
    files: tuple[ScopedFile, ...]
    """What the tree lists."""
    holds: Callable[[str], bool]
    """Whether a path, cleaned by `folder_path`, lies in the scope."""
    outside: str
    """Why a path that does not lie in the scope is refused."""


def attempt_tree(environment: Environment, attempt: Attempt) -> AttemptTree:
    scope = _scope(environment, attempt)
    return AttemptTree(scope.root, tuple(_tree_file(environment, scope, f) for f in scope.files))


def read_attempt_file(environment: Environment, attempt: Attempt, path: str) -> FileContent:
    """Raises UsageError for a path the rules refuse, and UnknownFileError for a file in the
    scope that does not exist."""
    scope = _scope(environment, attempt)
    try:
        cleaned = folder_path(path)
    except ValueError as error:
        raise UsageError(f"cannot read {path}: {error}") from None
    if not scope.holds(cleaned):
        raise UsageError(f"cannot read {path}: {scope.outside}")
    try:
        content = environment.workspace.read_within(scope.root, cleaned)
    except FileNotFoundError:
        raise UnknownFileError(cleaned, scope.root) from None
    except ValueError as error:
        raise UsageError(f"cannot read {path}: {error}") from None
    listed = next((file for file in scope.files if file.path == cleaned), None)
    return FileContent(listed or ScopedFile(cleaned, FileOrigin.YOURS), content)


def _scope(environment: Environment, attempt: Attempt) -> _Scope:
    language = attempt.language
    if language is None:
        return _single_file(
            layout.notes_path(environment.items.load(attempt.slug)), StartedFile.NOTES
        )
    problem = environment.problems.load(attempt.slug)
    if problem.meta.kind is ProblemKind.PROJECT:
        return _project(environment, problem, attempt.level_unlocked or FIRST_LEVEL)
    match language:
        case Language.JAVA | Language.KOTLIN | Language.GO:
            return _package(environment, problem, language)
        case Language.PYTHON | Language.TYPESCRIPT | Language.RUST:
            return _single_file(layout.stub_path(problem.meta, language), StartedFile.STUB)
        case _:
            assert_never(language)


def _single_file(path: str, origin: StartedFile) -> _Scope:
    file = PurePosixPath(path)
    root = str(file.parent)
    return _Scope(
        root,
        (ScopedFile(file.name, origin),),
        holds=lambda cleaned: cleaned == file.name,
        outside=f"not one of the attempt's files in {root}",
    )


def _package(environment: Environment, problem: Problem, language: Language) -> _Scope:
    """Every source file directly in the problem's package, as solution file targets count them
    (docs/specs/cli.md#solution-file-targets)."""
    root = layout.watch_path(problem.meta, language)
    stub = PurePosixPath(layout.stub_path(problem.meta, language)).name
    extension = f".{layout.SOURCE_EXTENSIONS[language]}"

    def holds(cleaned: str) -> bool:
        return PATH_SEPARATOR not in cleaned and cleaned.endswith(extension)

    names = {stub, *filter(holds, environment.workspace.tracked_files(root))}
    files = tuple(
        ScopedFile(name, StartedFile.STUB if name == stub else FileOrigin.YOURS)
        for name in sorted(names)
    )
    return _Scope(root, files, holds, f"not one of the attempt's {extension} files in {root}")


def _project(environment: Environment, problem: Problem, unlocked: int) -> _Scope:
    states = folder_states(environment, problem, unlocked)
    files = tuple(ScopedFile(file.path, file.origin, file.level, file.state) for file in states)
    root = project_folder(problem.meta.slug)
    return _Scope(root, files, holds=lambda cleaned: not is_untracked(cleaned), outside=TOOL_OUTPUT)


def _tree_file(environment: Environment, scope: _Scope, file: ScopedFile) -> TreeFile:
    try:
        content = environment.workspace.read_within(scope.root, file.path)
    except (FileNotFoundError, ValueError):
        return TreeFile(file, None, False)
    return TreeFile(file, len(content), _text(content) is not None)


def _text(content: bytes) -> str | None:
    if len(content) > EDITABLE_BYTES:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None
