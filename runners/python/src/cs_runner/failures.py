"""Exceptions from user code as the `error` object of an event (docs/specs/runners.md)."""

import traceback
from collections import deque
from dataclasses import dataclass
from pathlib import PurePath

from cs_runner.json_value import Json

MAX_TRACE_LINES = 10


@dataclass(frozen=True, slots=True)
class UserError:
    type: str
    message: str
    trace: str = ""
    """Frames in user code, innermost last, at most MAX_TRACE_LINES lines."""

    def to_json(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"type": self.type, "message": self.message}
        if self.trace:
            fields["trace"] = self.trace
        return fields


@dataclass(frozen=True, slots=True)
class UserFile:
    """A target file: only its frames are user code, shown by the file's name."""

    path: str

    def owns(self, file_name: str) -> bool:
        return file_name == self.path

    def shown(self, file_name: str) -> str:
        return PurePath(file_name).name


@dataclass(frozen=True, slots=True)
class UserFolder:
    """A project folder: every file under it is user code, shown relative to it."""

    root: str

    def owns(self, file_name: str) -> bool:
        return PurePath(file_name).is_relative_to(self.root)

    def shown(self, file_name: str) -> str:
        return PurePath(file_name).relative_to(self.root).as_posix()


type UserCode = UserFile | UserFolder


def describe(error: BaseException, code: UserCode) -> UserError:
    return UserError(type(error).__name__, str(error), _trace(error, code))


def _trace(error: BaseException, code: UserCode) -> str:
    lines: deque[str] = deque(maxlen=MAX_TRACE_LINES)
    for frame, line_number in traceback.walk_tb(error.__traceback__):
        file_name = frame.f_code.co_filename
        if code.owns(file_name):
            lines.append(f"{code.shown(file_name)}:{line_number} in {frame.f_code.co_qualname}")
    if isinstance(error, SyntaxError) and error.filename and code.owns(error.filename):
        lines.append(f"{code.shown(error.filename)}:{error.lineno}")
    return "\n".join(lines)
