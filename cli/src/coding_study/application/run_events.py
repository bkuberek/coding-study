"""The events of `cstudy test --events` and `cstudy submit --events`
(docs/specs/cli.md#event-stream).

A stream names its run once, then passes on what the run reports as it goes: progress notices,
each test or case as it starts and ends, diagnostics and graded levels. The command that writes
the stream ends it with the outcome and the exit code, which are the command's own.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from coding_study.application.submit_project import OpenedLevel
from coding_study.domain.attempts import Attempt
from coding_study.domain.diagnostics import Diagnostic
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.levels import LevelRun
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.project_test_runs import SuiteTestVerdict
from coding_study.domain.submissions import LevelTally


class RunCommand(StrEnum):
    TEST = "test"
    SUBMIT = "submit"


@dataclass(frozen=True, slots=True)
class RunStarted:
    """The run's options are checked and its work begins."""

    command: RunCommand
    meta: ProblemMeta
    attempt: Attempt
    language: Language
    levels: LevelRun
    """`ran_up_to` is the last level the run covers."""


@dataclass(frozen=True, slots=True)
class OutputLine:
    """A progress notice, such as `computing expected values ...`."""

    text: str


@dataclass(frozen=True, slots=True)
class SuiteTestStarted:
    """The runner started one test of the native suite (`cstudy test`)."""

    test_id: str


@dataclass(frozen=True, slots=True)
class SuiteTestReported:
    """One test of the native suite ended (`cstudy test`)."""

    verdict: SuiteTestVerdict


@dataclass(frozen=True, slots=True)
class CaseStarted:
    """The runner started one graded case (`cstudy submit`)."""

    case: RunnableCase
    level: int | None


@dataclass(frozen=True, slots=True)
class CaseGraded:
    """One graded case ended and was judged (`cstudy submit`)."""

    verdict: CaseVerdict
    level: int | None


@dataclass(frozen=True, slots=True)
class DiagnosticFound:
    diagnostic: Diagnostic


@dataclass(frozen=True, slots=True)
class LevelGraded:
    tally: LevelTally


@dataclass(frozen=True, slots=True)
class LevelOpened:
    opened: OpenedLevel


type RunEvent = (
    RunStarted
    | OutputLine
    | SuiteTestStarted
    | SuiteTestReported
    | CaseStarted
    | CaseGraded
    | DiagnosticFound
    | LevelGraded
    | LevelOpened
)
type EventSink = Callable[[RunEvent], None]
