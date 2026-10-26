"""Per-case capture of what user code prints (docs/specs/runners.md#execution-environment).

Standard output and standard error share one buffer, so the text reads as it would in a
terminal. Only the first MAX_OUTPUT_BYTES (UTF-8) are kept. Stress runs share one buffer between
all worker threads, so writes take a lock.
"""

import io
import threading
from collections.abc import Generator
from contextlib import contextmanager, redirect_stderr, redirect_stdout

MAX_OUTPUT_BYTES = 4096
TRUNCATION_NOTICE = "\n[output truncated at 4 KiB]\n"


class CapturedOutput(io.TextIOBase):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._kept_characters = 0
        self._overflowed = False
        self._lock = threading.Lock()

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        # A character takes at least one byte, so MAX_OUTPUT_BYTES characters always cover
        # the byte limit; text() trims to the exact byte count.
        with self._lock:
            room = MAX_OUTPUT_BYTES - self._kept_characters
            kept = text[: max(room, 0)]
            self._parts.append(kept)
            self._kept_characters += len(kept)
            self._overflowed = self._overflowed or len(kept) < len(text)
        return len(text)

    def text(self) -> str:
        text = "".join(self._parts)
        encoded = text.encode("utf-8", "surrogatepass")
        if len(encoded) <= MAX_OUTPUT_BYTES and not self._overflowed:
            return text
        return encoded[:MAX_OUTPUT_BYTES].decode("utf-8", "ignore") + TRUNCATION_NOTICE


@contextmanager
def capture_output() -> Generator[CapturedOutput]:
    output = CapturedOutput()
    with redirect_stdout(output), redirect_stderr(output):
        yield output
