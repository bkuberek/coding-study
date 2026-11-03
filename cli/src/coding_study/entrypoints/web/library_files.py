"""The files a definition names outside the attempt: the standard library, typeshed, `node_modules`,
`.venv`, the runner's support code (docs/specs/web-ui.md#definitions-and-library-files).

A file is read as it is, over links, as UTF-8 text up to 4 MiB. Never from the hidden directories
(docs/specs/web-ui.md#hidden-directories): cstudy's build area, where the reference solutions are,
the generated cases, the run data and the content root. The refusal applies to the path as named
and to the path its links lead to, and finds a directory by what it is (its device and inode), so
neither a link nor another spelling of the same directory on a case-insensitive file system gets
past it. The checks come in the order the spec fixes.
"""

import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.parse import unquote, urlsplit

LIMIT = 4 * 1024 * 1024
LOCAL_HOSTS = ("", "localhost")


class Reason(StrEnum):
    """Why a file is not shown, in the order the checks come."""

    NOT_A_DEFINITION = "not_a_definition"
    NOT_A_FILE_URI = "not_a_file_uri"
    BUILD_AREA = "build_area"
    MISSING = "missing"
    NOT_A_FILE = "not_a_file"
    TOO_LARGE = "too_large"
    NOT_TEXT = "not_text"

    @property
    def message(self) -> str:
        return _MESSAGES[self]


_MESSAGES = {
    Reason.NOT_A_DEFINITION: "not a definition target of this session",
    Reason.NOT_A_FILE_URI: "not a file: URI",
    Reason.BUILD_AREA: "not shown: cstudy's build area",
    Reason.MISSING: "no such file",
    Reason.NOT_A_FILE: "not a regular file",
    Reason.TOO_LARGE: "over 4 MiB",
    Reason.NOT_TEXT: "not UTF-8 text",
}


@dataclass(frozen=True, slots=True)
class LibraryFile:
    uri: str
    """As the request named it."""
    path: str
    """Relative to the workspace root when the file is inside it, else absolute with the home
    directory written `~`."""
    text: str


class LibraryRefusalError(Exception):
    def __init__(self, reason: Reason, path: str) -> None:
        super().__init__(reason.message)
        self.reason = reason
        self.path = path
        """What the refusal names: the path as displayed, or the URI when it is no file."""


def read_library_file(uri: str, workspace: Path, hidden: Sequence[Path]) -> LibraryFile:
    """The file `uri` names, unless it lies in one of the `hidden` directories.

    Raises LibraryRefusalError, with the first reason that applies after `NOT_A_DEFINITION`,
    which the caller checks.
    """
    named = file_path(uri)
    shown = display_path(named, workspace)
    if _under_any(named, hidden):
        raise LibraryRefusalError(Reason.BUILD_AREA, shown)
    try:
        resolved = Path(os.path.realpath(named))
    except ValueError:
        raise LibraryRefusalError(Reason.MISSING, shown) from None
    if _under_any(resolved, hidden):
        raise LibraryRefusalError(Reason.BUILD_AREA, shown)
    return LibraryFile(uri, shown, _text(resolved, shown))


def is_hidden(uri: str, hidden: Sequence[Path]) -> bool:
    """Whether `uri` names a file that lies in one of the `hidden` directories, as named or with
    its links resolved. A URI that is no file of this machine, or that no file can have, is not."""
    try:
        named = file_path(uri)
        return _under_any(named, hidden) or _under_any(Path(os.path.realpath(named)), hidden)
    except (LibraryRefusalError, ValueError):
        return False


def local_path(uri: str) -> str:
    """The absolute path of a `file:` URI of this machine, percent-decoded, as the URI spells
    it. Raises LibraryRefusalError `NOT_A_FILE_URI` for any other URI."""
    try:
        parts = urlsplit(uri)
    except ValueError:
        raise LibraryRefusalError(Reason.NOT_A_FILE_URI, uri) from None
    local = parts.scheme.lower() == "file" and parts.netloc.lower() in LOCAL_HOSTS
    path = unquote(parts.path)
    if not local or parts.query or parts.fragment or not path.startswith("/"):
        raise LibraryRefusalError(Reason.NOT_A_FILE_URI, uri)
    return path


def file_path(uri: str) -> Path:
    return Path(local_path(uri))


def display_path(path: Path, workspace: Path) -> str:
    if path.is_relative_to(workspace):
        return path.relative_to(workspace).as_posix()
    home = Path.home()
    if path.is_relative_to(home):
        return f"~/{path.relative_to(home).as_posix()}"
    return str(path)


def _under_any(path: Path, directories: Sequence[Path]) -> bool:
    return any(_is_under(path, directory) for directory in directories)


def _is_under(path: Path, directory: Path) -> bool:
    """Whether `path` is `directory` or lies in it, by name or by identity: some ancestor of
    `path` is the same directory on the disk, however its name is spelt."""
    if path.is_relative_to(directory):
        return True
    try:
        wanted = directory.stat()
    except (OSError, ValueError):
        return False
    for ancestor in (path, *path.parents):
        try:
            if os.path.samestat(ancestor.stat(), wanted):
                return True
        except (OSError, ValueError):
            continue
    return False


def _text(resolved: Path, shown: str) -> str:
    """The file's text. It opens without following a link (the path is resolved) and without
    waiting for a pipe, and is checked after it is open, so what is read is what was checked."""
    try:
        descriptor = os.open(resolved, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except (OSError, ValueError):
        raise LibraryRefusalError(Reason.MISSING, shown) from None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise LibraryRefusalError(Reason.NOT_A_FILE, shown)
        if info.st_size > LIMIT:
            raise LibraryRefusalError(Reason.TOO_LARGE, shown)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(LIMIT + 1)
    finally:
        os.close(descriptor)
    if len(data) > LIMIT:
        raise LibraryRefusalError(Reason.TOO_LARGE, shown)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise LibraryRefusalError(Reason.NOT_TEXT, shown) from None
