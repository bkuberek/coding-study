"""The events of `cstudy test --events` and `cstudy submit --events`
(docs/specs/cli.md#event-stream).

A stream names its run once, then passes on what the run reports as it goes: progress notices,
the build, each test, case or stress run as it starts and ends, revisions, diagnostics, graded
and opened levels, and the `--perf` check. The command that writes the stream ends it with the
outcome and the exit code, which are the command's own.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from coding_study.application.run_bench import BenchResult
from coding_study.application.submit_project import OpenedLevel
from coding_study.domain.attempts import Attempt
from coding_study.domain.diagnostics import Diagnostic
from coding_study.domain.generated_cases import OracleInput
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.levels import LevelRun
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.project_test_runs import SuiteTestVerdict
from coding_study.domain.stress_runs import PlannedRun
from coding_study.domain.stress_verdict import StressRunResult, StressVerdict
from coding_study.domain.submissions import LevelTally
from coding_study.domain.time_limits import TimeLimit


class RunCommand(StrEnum):
    TEST = "test"
    SUBMIT = "submit"


@dataclass(frozen=True, slots=True)
class StressPlan:
    """A concurrent run's stress runs: so many stress cases, variants, and runs of each."""

    cases: int
    variants: int
    runs: int


@dataclass(frozen=True, slots=True)
class PlannedCases:
    """What a run of a problem that is not a project will report, as its report's header counts
    it."""

    cases: int
    """The cases, the sequential ones of a concurrent problem."""
    visible: int
    hidden: int
    generated: int
    oracle_inputs: int
    stress: StressPlan | None
    """None but for a concurrent problem."""


@dataclass(frozen=True, slots=True)
class RunStarted:
    """The run's options are checked and its work begins."""

    command: RunCommand
    meta: ProblemMeta
    attempt: Attempt
    language: Language
    levels: LevelRun | None
    """`ran_up_to` is the last level the run covers; None for a problem without levels."""
    at: datetime
    """When the run began, for the elapsed time of the attempt's time box."""
    time_limit: TimeLimit | None = None
    """The time limit the run asks for; None when time limits are off."""
    planned: PlannedCases | None = None
    """None for a project, whose suite's size is known only as it runs."""


@dataclass(frozen=True, slots=True)
class OutputLine:
    """A progress notice, such as `computing expected values ...`."""

    text: str


@dataclass(frozen=True, slots=True)
class BuildEnded:
    """The build or type check of a language or option that has one ended, built or not."""

    seconds: float
    note: str | None
    """`gradle, warm`; None when the build failed."""


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
    """The runner started one graded case or oracle input."""

    case: RunnableCase
    level: int | None
    oracle: OracleInput | None = None
    """Set for an oracle input of `cstudy test --stress N`."""


@dataclass(frozen=True, slots=True)
class CaseGraded:
    """One graded case or oracle input ended and was judged by the comparator."""

    verdict: CaseVerdict
    level: int | None
    oracle: OracleInput | None = None
    """Set for an oracle input of `cstudy test --stress N`."""


@dataclass(frozen=True, slots=True)
class CaseRevised:
    """A case whose verdict the run's time limits changed, once they are known."""

    verdict: CaseVerdict
    level: int | None


@dataclass(frozen=True, slots=True)
class StressRunStarted:
    """The runner started one stress run of a concurrent problem, or of a project's stress case
    in `cstudy submit`."""

    planned: PlannedRun
    level: int | None = None
    """A project's stress case: its level; None for a concurrent problem."""


@dataclass(frozen=True, slots=True)
class StressRunJudged:
    """One stress run ended and was judged against its invariants."""

    planned: PlannedRun
    result: StressRunResult
    level: int | None = None
    """As `StressRunStarted.level`."""


@dataclass(frozen=True, slots=True)
class StressGraded:
    """Every run of one stress case and variant was judged."""

    verdict: StressVerdict
    level: int | None = None
    """As `StressRunStarted.level`."""


@dataclass(frozen=True, slots=True)
class DiagnosticFound:
    diagnostic: Diagnostic


@dataclass(frozen=True, slots=True)
class LevelGraded:
    tally: LevelTally


@dataclass(frozen=True, slots=True)
class LevelOpened:
    opened: OpenedLevel


@dataclass(frozen=True, slots=True)
class PerfChecked:
    """The short bench of `cstudy test --perf`, after a full pass."""

    bench: BenchResult


type RunEvent = (
    RunStarted
    | OutputLine
    | BuildEnded
    | SuiteTestStarted
    | SuiteTestReported
    | CaseStarted
    | CaseGraded
    | CaseRevised
    | StressRunStarted
    | StressRunJudged
    | StressGraded
    | DiagnosticFound
    | LevelGraded
    | LevelOpened
    | PerfChecked
)
type EventSink = Callable[[RunEvent], None]
