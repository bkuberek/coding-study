"""Starting a binary that `cstudy` wrote a moment ago.

`cstudy` copies a built Go or Rust binary into a private folder and starts it at once. The copy is
written by this process while other threads keep starting children (one per language in
`cstudy verify`), and a child forked while the copy is open for writing holds that descriptor until
its own `exec`. Until then the kernel refuses to execute the copy with `ETXTBSY` ("Text file
busy"). The refusal ends within a fraction of a second, so the start is tried again; any other
failure is the caller's at once.
"""

import errno
import time
from collections.abc import Callable

MAX_ATTEMPTS = 10
FIRST_DELAY_SECONDS = 0.01
MAX_DELAY_SECONDS = 0.5
"""The delay doubles from the first to this one: the attempts wait about 2 s in all."""


def start_when_not_busy[T](start: Callable[[], T]) -> T:
    """The result of `start`, which is tried again while it raises `OSError` with `ETXTBSY`, up to
    `MAX_ATTEMPTS` times. Raises that error after the last attempt, and any other `OSError` at
    once."""
    delay = FIRST_DELAY_SECONDS
    for _ in range(MAX_ATTEMPTS - 1):
        try:
            return start()
        except OSError as error:
            if error.errno != errno.ETXTBSY:
                raise
        time.sleep(delay)
        delay = min(delay * 2, MAX_DELAY_SECONDS)
    return start()
