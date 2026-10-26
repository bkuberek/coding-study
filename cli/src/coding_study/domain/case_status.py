"""The statuses `cstudy test` prints (docs/specs/cli.md#cstudy-test)."""

from enum import StrEnum


class CaseStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    TLE = "TLE"
    """Correct, but slower than the optional time limit."""
    INVALID = "INVALID"
    STALLED = "STALLED"
    """A concurrent stress run was still unfinished at its deadline."""
    NOT_RUN = "NOT RUN"
