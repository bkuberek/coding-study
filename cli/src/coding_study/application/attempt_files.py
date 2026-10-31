"""An attempt's files, as the web UI's file tree and editor show them and change them
(docs/specs/web-ui.md#file-api-rules).

Each attempt has a root and a scope: a project its folder, a single-file problem on the JVM or in
Go its package directory, any other problem the directory of its file, an item its track's notes
directory. Paths are relative to the root; none may leave it, and no link on the way is followed.
Files are created, moved and deleted only in a project folder and a JVM or Go package.
"""

import hashlib
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import assert_never

from coding_study.application.active_attempt import attempt_in_progress
from coding_study.application.environment import Environment
from coding_study.application.project_manifest import folder_states
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import (
    FileChangedError,
    FileTooLargeError,
    UnknownFileError,
    UsageError,
)
from coding_study.domain.file_states import FileState
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, Problem, ProblemKind
from coding_study.domain.project import PATH_SEPARATOR
from coding_study.domain.project_manifest import (
    FileOrigin,
    content_digest,
    folder_path,
    project_lock,
)
from coding_study.domain.workspace_projects import is_untracked, project_folder

EDITABLE_BYTES = 1024 * 1024
"""UTF-8 text up to 1 MiB opens in an editor; any other file opens read-only."""
TOOL_OUTPUT = "the page never shows what tools write (.venv, node_modules, caches, build output)"


class StartedFile(StrEnum):
    """The file `cstudy start` wrote for a single-file problem or an item."""

    STUB = "stub"
    NOTES = "notes"


class _Verb(StrEnum):
    """What a refusal says could not be done."""

    READ = "read"
    SAVE = "save"
    CREATE = "create"


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
    fixed: str | None = None
    """Why no file may be created, moved or deleted; None where they may."""
    lock: str | None = None
    """The lock a change holds, relative to the workspace root: a project's."""


@dataclass(frozen=True, slots=True)
class SavedFile:
    path: str
    """Relative to the attempt's root, without `.` and `..` segments."""
    sha256: str
    """Of the content now on disk, the file's next `ETag`."""


def attempt_tree(environment: Environment, attempt: Attempt) -> AttemptTree:
    scope = _scope(environment, attempt)
    return AttemptTree(scope.root, tuple(_tree_file(environment, scope, f) for f in scope.files))


def read_attempt_file(environment: Environment, attempt: Attempt, path: str) -> FileContent:
    """Raises UsageError for a path the rules refuse, and UnknownFileError for a file in the
    scope that does not exist."""
    scope = _scope(environment, attempt)
    cleaned = _scoped_path(scope, _Verb.READ, path)
    try:
        content = environment.workspace.read_within(scope.root, cleaned)
    except FileNotFoundError:
        raise UnknownFileError(cleaned, scope.root) from None
    except ValueError as error:
        raise UsageError(f"cannot read {path}: {error}") from None
    listed = next((file for file in scope.files if file.path == cleaned), None)
    return FileContent(listed or ScopedFile(cleaned, FileOrigin.YOURS), content)


class AttemptFileChanges:
    """The web UI's changes to the files of an attempt in progress
    (docs/specs/web-ui.md#file-api-rules).

    Each change in a project folder holds the project's lock, waiting at most `lock_deadline_s`
    for it (LockBusyError past that), so it never interleaves with a restore, an unlock or a
    start; then it checks that the attempt is still the one in progress. Paths follow the rules
    `read_attempt_file` reads by; a refused path raises UsageError with the rule's reason.
    """

    def __init__(self, environment: Environment, attempt: Attempt, lock_deadline_s: float) -> None:
        self._environment = environment
        self._attempt = attempt
        self._lock_deadline_s = lock_deadline_s
        self._scope = _scope(environment, attempt)

    def save(self, path: str, text: str, expected_sha256: str) -> SavedFile:
        """Writes `text` over the file, while its content still has the SHA-256
        `expected_sha256`, the `ETag` the page read it with.

        Raises FileChangedError when the file changed or went since, FileTooLargeError for text
        over `EDITABLE_BYTES`, and UsageError for a file that is not text the page edits.
        """
        cleaned = _scoped_path(self._scope, _Verb.SAVE, path)
        _require_editable_size(_Verb.SAVE, cleaned, text)
        with self._changing():
            current = self._current(_Verb.SAVE, cleaned)
            if current is None:
                raise FileChangedError(f"{cleaned} was deleted since the page read it", None)
            if _sha256(current) != expected_sha256:
                message = f"{cleaned} changed since the page read it"
                raise FileChangedError(message, _sha256(current))
            if _text(current) is None:
                raise UsageError(f"cannot save {cleaned}: it is not UTF-8 text up to 1 MiB")
            self._write(_Verb.SAVE, cleaned, text)
        return SavedFile(cleaned, content_digest(text))

    def create(self, path: str, text: str) -> SavedFile:
        """Writes `text` to a new file, making the directories on the way.

        Raises FileChangedError when a file is already there, FileTooLargeError for text over
        `EDITABLE_BYTES`, and UsageError where the attempt's kind creates no files.
        """
        cleaned = self._reshapable_path(_Verb.CREATE, path)
        _require_editable_size(_Verb.CREATE, cleaned, text)
        with self._changing():
            current = self._current(_Verb.CREATE, cleaned)
            if current is not None:
                raise FileChangedError(f"cannot create {cleaned}: it exists", _sha256(current))
            self._write(_Verb.CREATE, cleaned, text)
        return SavedFile(cleaned, content_digest(text))

    def _reshapable_path(self, verb: _Verb, path: str) -> str:
        """`path` cleaned, where the attempt's kind lets files be created, moved and deleted."""
        if self._scope.fixed is not None:
            raise UsageError(f"cannot {verb} {path}: {self._scope.fixed}")
        return _scoped_path(self._scope, verb, path)

    @contextmanager
    def _changing(self) -> Generator[None]:
        with self._locked():
            attempt_in_progress(self._environment.progress, self._attempt.id)
            yield

    def _locked(self) -> AbstractContextManager[None]:
        lock = self._scope.lock
        if lock is None:
            return nullcontext()
        return self._environment.workspace.locked_with_deadline(lock, self._lock_deadline_s)

    def _current(self, verb: _Verb, cleaned: str) -> bytes | None:
        """The file's content; None when no file is there."""
        try:
            return self._environment.workspace.read_within(self._scope.root, cleaned)
        except FileNotFoundError:
            return None
        except ValueError as error:
            raise UsageError(f"cannot {verb} {cleaned}: {error}") from None

    def _write(self, verb: _Verb, cleaned: str, text: str) -> None:
        try:
            self._environment.workspace.write_within(self._scope.root, cleaned, text)
        except ValueError as error:
            raise UsageError(f"cannot {verb} {cleaned}: {error}") from None


def _scoped_path(scope: _Scope, verb: _Verb, path: str) -> str:
    """`path` without `.` and `..` segments; raises UsageError when it leaves the root, is
    absolute, uses `\\`, or lies outside the scope."""
    try:
        cleaned = folder_path(path)
    except ValueError as error:
        raise UsageError(f"cannot {verb} {path}: {error}") from None
    if not scope.holds(cleaned):
        raise UsageError(f"cannot {verb} {path}: {scope.outside}")
    return cleaned


def _require_editable_size(verb: _Verb, cleaned: str, text: str) -> None:
    if len(text.encode()) > EDITABLE_BYTES:
        raise FileTooLargeError(
            f"cannot {verb} {cleaned}: the text is over 1 MiB, the most the page edits"
        )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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
        fixed=f"the attempt has one file, {file.name}",
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
    slug = problem.meta.slug
    return _Scope(
        project_folder(slug),
        files,
        holds=lambda cleaned: not is_untracked(cleaned),
        outside=TOOL_OUTPUT,
        lock=project_lock(slug),
    )


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
