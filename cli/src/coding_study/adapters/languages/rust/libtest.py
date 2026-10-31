"""What a Rust test's own process says about it (docs/specs/runners.md#rust-projects).

Each test runs as `<binary> --exact <name> --nocapture`, with standard output and error in one
pipe. libtest's stable output is text meant for people, so the exit code decides: 0 passed or was
ignored, 101 failed, anything else crashed. The text is read only for what the exit code cannot
say: whether a passing run passed or ignored its test (libtest's `test result:` line), why it
failed (the panic's message and location, or libtest's note), and what the test printed.

Under `--nocapture` libtest prints `running 1 test`, then the test runs and prints, a panic adds
its message, and only then does libtest print `test <name> ... <result>`: what the test printed is
the text between the two, without the panic. Output that the test left without a final newline
comes out joined to libtest's result line, so the result is found by its text, not at a line's
start.
"""

import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from coding_study.domain.runs import Crashed, Raised, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, Skipped, SuiteOutcome

PASSED_EXIT = 0
FAILED_EXIT = 101
"""libtest's exit code when a test failed; any other but 0 is a crash."""
LIBTEST_ERROR = "libtest"
OUTPUT_LIMIT_BYTES = 4096
TRUNCATION_NOTICE = "\n[output truncated at 4 KiB]\n"
CRASH_TAIL_LINES = 20
_LISTED_TEST = ": test"
_RUNNING = "running 1 test\n"
_SHOULD_PANIC = " - should panic"
_IGNORED = "ignored"
_IGNORED_REASON = "ignored, "
_RETURNED_ERROR = "Error: "
_SUMMARY = re.compile(
    r"test result: \w+\. (?P<passed>\d+) passed; \d+ failed; (?P<ignored>\d+) ignored"
)
_PANIC = re.compile(
    r"\n?thread '[^'\n]*'(?: \(\d+\))? panicked at (?P<location>[^\n]*):\n(?P<message>.*?)"
    r"(?:\nnote: run with `RUST_BACKTRACE=1` environment variable to display a backtrace\n|\n?\Z)",
    re.DOTALL,
)
"""The panic hook's lines: the location, the message (several lines, perhaps), and the note it
adds while `RUST_BACKTRACE` is unset, which ends the message."""


@dataclass(frozen=True, slots=True)
class FinishedTest:
    """One test's process, after it ended."""

    exit_code: int
    """128 plus the signal's number when a signal ended it (an abort is 134)."""
    output: str
    """Its standard output and standard error, together."""
    duration_ns: int


def listed_tests(listing: str) -> tuple[str, ...]:
    """The tests of `<binary> --list --format terse`, in its order: the lines `<name>: test`."""
    return tuple(
        line.removesuffix(_LISTED_TEST)
        for line in listing.splitlines()
        if line.endswith(_LISTED_TEST)
    )


def finished_outcome(name: str, finished: FinishedTest, root: Path) -> SuiteOutcome:
    """The outcome of the test `name`, from its process; panic locations under `root` are named
    relative to it."""
    report = _Report.read(name, finished.output)
    if finished.exit_code == PASSED_EXIT:
        return _passed(name, report, finished.duration_ns)
    if finished.exit_code == FAILED_EXIT:
        return _failed(report, finished, root)
    lines = report.body.splitlines()
    return Crashed(finished.exit_code, tuple(deque(lines, maxlen=CRASH_TAIL_LINES)))


def _passed(name: str, report: "_Report", duration: int) -> SuiteOutcome:
    """A run that libtest ended well: the test passed, was ignored, or was not there to run."""
    if report.counts("passed"):
        return Passed(duration, report.printed())
    if report.counts("ignored"):
        return Skipped(report.ignore_reason(), duration)
    message = f"the test did not run: libtest found no test named {name}"
    return Raised(UserError(LIBTEST_ERROR, message), duration)


def _failed(report: "_Report", finished: FinishedTest, root: Path) -> SuiteOutcome:
    """A failed test, or libtest refusing to run it (no result line at all)."""
    duration = finished.duration_ns
    if report.result is None:
        return Raised(UserError(LIBTEST_ERROR, finished.output.strip()), duration)
    return AssertionFailed(report.failure(root), duration, report.printed())


DEBUGGED_EXIT = -1
"""The exit code of a debugged test that crashed: the debugger has it, `cstudy` does not."""


def debugged_outcome(name: str, output: str, root: Path) -> SuiteOutcome:
    """The outcome of the test `name` that ran under the debug server, whose exit code is the
    debugger's: libtest's result line says how it ended, and its absence that it crashed. A
    debugged run has no durations."""
    report = _Report.read(name, output)
    if report.result is None:
        lines = report.body.splitlines()
        return Crashed(DEBUGGED_EXIT, tuple(deque(lines, maxlen=CRASH_TAIL_LINES)))
    if report.counts("passed") or report.counts("ignored"):
        return _passed(name, report, 0)
    return AssertionFailed(report.failure(root), 0, report.printed())


@dataclass(frozen=True, slots=True)
class _Report:
    name: str
    body: str
    """What came between `running 1 test` and libtest's result line: the test's own output and
    its panic; everything after `running 1 test` when there is no result line."""
    result: str | None
    """The text after `test <name> ... `: `ok`, `FAILED`, `ignored, <reason>`."""
    after: str
    """libtest's lines after the result: the failures and the summary."""

    @classmethod
    def read(cls, name: str, output: str) -> "_Report":
        start = output.find(_RUNNING)
        text = output[start + len(_RUNNING) :] if start >= 0 else output
        markers = (f"test {name} ... ", f"test {name}{_SHOULD_PANIC} ... ")
        found = max((text.rfind(marker), marker) for marker in markers)
        position, marker = found
        if position < 0:
            return cls(name, text, None, "")
        result, _, after = text[position + len(marker) :].partition("\n")
        return cls(name, text[:position], result, after)

    def counts(self, which: str) -> bool:
        summary = _SUMMARY.search(self.after)
        return summary is not None and summary[which] == "1"

    def ignore_reason(self) -> str:
        if self.result is not None and self.result.startswith(_IGNORED_REASON):
            return self.result.removeprefix(_IGNORED_REASON)
        return _IGNORED

    def printed(self) -> str:
        """What the test printed, without its panic or the error it returned."""
        text = _PANIC.sub("", self.body)
        lines = text.splitlines(keepends=True)
        if lines and lines[-1].startswith(_RETURNED_ERROR):
            lines.pop()
        return _capped("".join(lines))

    def failure(self, root: Path) -> str:
        """The panic's message and location, else libtest's note on the failure, else the error
        the test returned."""
        panic = _PANIC.search(self.body)
        if panic is not None:
            location = _relative(panic["location"], root)
            return f"{panic['message'].rstrip()}\nat {location}"
        section = f"---- {self.name} stdout ----\n"
        if section in self.after:
            note = self.after.split(section, 1)[1].split("\n\n", 1)[0]
            return note.strip()
        lines = self.body.splitlines()
        if lines and lines[-1].startswith(_RETURNED_ERROR):
            return lines[-1]
        return "the test failed"


def _relative(location: str, root: Path) -> str:
    return location.removeprefix(f"{root}/")


def _capped(text: str) -> str:
    """At most 4 KiB of UTF-8, never splitting a character, with a notice when anything was
    dropped (docs/specs/runners.md#execution-environment)."""
    encoded = text.encode()
    if len(encoded) <= OUTPUT_LIMIT_BYTES:
        return text
    kept = encoded[:OUTPUT_LIMIT_BYTES].decode(errors="ignore")
    return kept + TRUNCATION_NOTICE
