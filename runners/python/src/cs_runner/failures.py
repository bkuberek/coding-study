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
    """Frames in the target file, innermost last, at most MAX_TRACE_LINES lines."""

    def to_json(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"type": self.type, "message": self.message}
        if self.trace:
            fields["trace"] = self.trace
        return fields


def describe(error: BaseException, user_file: str) -> UserError:
    return UserError(type(error).__name__, str(error), _trace(error, user_file))


def _trace(error: BaseException, user_file: str) -> str:
    file_name = PurePath(user_file).name
    lines: deque[str] = deque(maxlen=MAX_TRACE_LINES)
    for frame, line_number in traceback.walk_tb(error.__traceback__):
        if frame.f_code.co_filename == user_file:
            lines.append(f"{file_name}:{line_number} in {frame.f_code.co_qualname}")
    if isinstance(error, SyntaxError) and error.filename == user_file:
        lines.append(f"{file_name}:{error.lineno}")
    return "\n".join(lines)
