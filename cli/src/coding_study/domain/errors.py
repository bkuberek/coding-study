from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentIssue:
    """One problem in a content file; `location` is a field path or a line position."""

    file: str
    location: str
    message: str

    def __str__(self) -> str:
        if not self.location:
            return f"{self.file}: {self.message}"
        return f"{self.file}: {self.location}: {self.message}"


class ContentError(Exception):
    """Problem files that fail schema or structural validation (exit code 5)."""

    def __init__(self, issues: Sequence[ContentIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(str(issue) for issue in self.issues))


class UnknownProblemError(LookupError):
    def __init__(self, slug: str) -> None:
        super().__init__(f'unknown problem "{slug}"')
        self.slug = slug


class ConfigError(Exception):
    """An unreadable or invalid user config file."""

    def __init__(self, source: str, issues: Sequence[str]) -> None:
        self.source = source
        self.issues = tuple(issues)
        super().__init__(f"{source}: " + "; ".join(self.issues))


class LanguageNotSetUpError(Exception):
    """A language whose stub generator or runner is not implemented yet (exit code 4)."""

    def __init__(self, language: str, component: str) -> None:
        super().__init__(f"{language} {component} is not set up yet")
        self.language = language
        self.component = component


class RunnerStartError(Exception):
    """A runner that could not be launched or did not say hello in time (exit code 4)."""

    def __init__(self, message: str, stderr_tail: Sequence[str] = ()) -> None:
        self.stderr_tail = tuple(stderr_tail)
        super().__init__("\n".join((message, *self.stderr_tail)))


class RunnerProtocolError(Exception):
    """A runner that broke the protocol in docs/specs/runners.md (exit code 70)."""


class UsageError(Exception):
    """A request the command cannot honor, such as no active attempt (exit code 3)."""


class VersionControlError(Exception):
    """git is missing, or cannot compare the repository with a branch (exit code 4)."""


class UnknownAttemptError(LookupError):
    """No attempt has the id the web UI asked for."""

    def __init__(self, attempt_id: int) -> None:
        super().__init__(f"unknown attempt {attempt_id}")
        self.attempt_id = attempt_id


class AttemptEndedError(Exception):
    """The web UI asked for an attempt that is no longer in progress, or that another attempt of
    the same problem and language replaced."""

    def __init__(self, attempt_id: int, slug: str) -> None:
        super().__init__(f"attempt {attempt_id} of {slug} is no longer in progress")
        self.attempt_id = attempt_id


class UnknownFileError(LookupError):
    """No file at a path the web UI asked for in an attempt's files."""

    def __init__(self, path: str, root: str) -> None:
        super().__init__(f"no file {path} in {root}")
        self.path = path


class LockBusyError(Exception):
    """Another `cstudy` held a lock past the deadline the web UI waits for it."""

    def __init__(self, lock: str, deadline_s: float) -> None:
        super().__init__(
            f"another cstudy command held {lock} for {deadline_s:g} s; try again once it ends"
        )
