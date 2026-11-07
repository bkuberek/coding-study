"""Ports the application drives; adapters implement them (docs/architecture.md)."""

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from coding_study.application.installs import InstallScan
from coding_study.domain.about import Credit
from coding_study.domain.attempts import Attempt, NewAttempt, RunRecord
from coding_study.domain.bench_records import (
    BenchOutcome,
    BenchRunRecord,
    BenchRunSummary,
    MachineState,
)
from coding_study.domain.bench_runs import BenchReport, BenchRequest
from coding_study.domain.bench_verdict import PastRun
from coding_study.domain.cases import JsonValue
from coding_study.domain.code_intelligence import LanguageServer
from coding_study.domain.comparators import Checker
from coding_study.domain.config import Config
from coding_study.domain.config_keys import ConfigView
from coding_study.domain.debugging import DebugSession
from coding_study.domain.docker_engine import EngineState
from coding_study.domain.generated_cases import GeneratedCase
from coding_study.domain.invariants import StressChecker
from coding_study.domain.items import ItemMeta
from coding_study.domain.jdk import SelectedJdk
from coding_study.domain.problem import Language, Problem, ProblemMeta, ProblemSummary
from coding_study.domain.problem_sets import ProblemSet
from coding_study.domain.progress_export import ProgressSnapshot
from coding_study.domain.progress_stats import LatestBench
from coding_study.domain.project_tests import LevelTests
from coding_study.domain.runs import CaseReport, RunReport, RunRequest
from coding_study.domain.sandbox import (
    CommandOutcome,
    InstallPlan,
    LeftoverStack,
    ReadyStack,
    SandboxInventory,
    SandboxUser,
    StackIdentity,
    StackPlan,
    StartupBudget,
)
from coding_study.domain.scheduling import ProblemProgress, ScheduleEntry
from coding_study.domain.submissions import LevelUnlock, SubmissionRecord
from coding_study.domain.suite_runs import SuiteJob, SuiteReport, SuiteTest
from coding_study.domain.time_limits import Calibration


class ProblemRepository(Protocol):
    def load(self, slug: str) -> Problem:
        """Raises UnknownProblemError for an unknown slug and ContentError for invalid files."""
        ...

    def list_summaries(self) -> tuple[ProblemSummary, ...]:
        """Every problem in id order; raises ContentError listing every invalid meta.yaml."""
        ...


class ItemRepository(Protocol):
    """Non-autograded items in `tracks/<track>/<slug>/` (docs/specs/content.md)."""

    def slugs(self) -> tuple[str, ...]:
        """The slug of every item directory, in directory order (duplicates kept)."""
        ...

    def directories(self) -> tuple[str, ...]:
        """Every item directory, repository-relative, in the order of `slugs`."""
        ...

    def item_directory(self, slug: str) -> str:
        """Repository-relative, e.g. `tracks/system-design/url-shortener`; raises
        UnknownProblemError."""
        ...

    def load(self, slug: str) -> ItemMeta:
        """Raises UnknownProblemError for an unknown slug and ContentError for an invalid
        item.yaml."""
        ...

    def list_items(self) -> tuple[ItemMeta, ...]:
        """Every item in directory order; raises ContentError listing every invalid item.yaml."""
        ...

    def read_text(self, slug: str, name: str) -> str | None:
        """`name` is relative to the item directory; None when the file does not exist."""
        ...

    def file_names(self, slug: str, directory: str = "") -> tuple[str, ...]:
        """Sorted names of the files (not directories) in an item subdirectory."""
        ...


class ProblemSetStore(Protocol):
    """The workspace's `sets.yaml` (docs/decisions/0023-problem-sets.md). Every method raises
    ConfigError, leaving the file as it is, for a file that does not parse or is invalid. A change
    keeps the lines of the file it does not touch, and is atomic."""

    def read(self) -> tuple[ProblemSet, ...]:
        """The sets, in the file's order; none when there is no file."""
        ...

    def add(self, problem_set: ProblemSet) -> None:
        """Adds a set after the others, making the file when missing."""
        ...

    def set_problems(self, name: str, slugs: tuple[str, ...]) -> None:
        """Gives the set named `name`, which must exist, these slugs in this order."""
        ...

    def rename(self, name: str, new_name: str) -> None: ...

    def delete(self, name: str) -> None: ...


class StudyGuides(Protocol):
    """The user's own study guides under config `study_guides.root`; never part of the content."""

    def locate(self, path: str) -> str | None:
        """A link to the guide file at `path`, relative to the root; None when no root is
        configured or no such file exists under it."""
        ...


class ConfigSource(Protocol):
    @property
    def location(self) -> str: ...

    def exists(self) -> bool: ...

    def load(self) -> Config:
        """Built-in defaults when the file does not exist; raises ConfigError when invalid."""
        ...


@dataclass(frozen=True, slots=True)
class ProbeResult:
    exit_code: int
    output: str
    """Standard output and standard error, combined."""


class ToolProbe(Protocol):
    def run(self, command: Sequence[str]) -> ProbeResult | None:
        """Run a short command such as `node --version`; None when the executable is missing."""
        ...


class CommandRunner(Protocol):
    def run(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None = None
    ) -> ProbeResult | None:
        """Run a setup command such as `uv sync` to completion, without a time limit; None when
        the executable is missing. `environment` is set for the command on top of the process's
        own."""
        ...


class RepositoryFiles(Protocol):
    """Files under one root: a workspace or a content root."""

    @property
    def root(self) -> Path: ...

    def exists(self, relative_path: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class ScaffoldOutcome:
    written: tuple[str, ...]
    """Workspace-relative files created, the marker included."""
    kept: tuple[str, ...]
    """Template files that already existed and were left as they were."""


class WorkspaceSetup(Protocol):
    """The workspace template, the marker and the runner runtime
    (docs/specs/installation-and-workspaces.md)."""

    def workspace_at_or_above(self, directory: Path) -> Path | None: ...

    def checkout_at_or_above(self, directory: Path) -> Path | None:
        """The nearest content checkout (problems/ and schemas/) at or above `directory`."""
        ...

    def missing_files(self, root: Path) -> tuple[str, ...]:
        """Template files, and the marker, that `root` lacks."""
        ...

    def write_missing(self, root: Path) -> ScaffoldOutcome:
        """Create `root` and every missing template file and the marker; never overwrite."""
        ...

    def runtime_current(self, root: Path) -> bool: ...

    def refresh_runtime(self, root: Path) -> None:
        """Bring `.cs/runtime/` in step with the content's runners."""
        ...

    def init_git(self, root: Path) -> None:
        """`git init` in `root`; raises VersionControlError when git is missing or fails."""
        ...


class StubGenerator(Protocol):
    """One per language (docs/specs/runners.md#stub-generation)."""

    def generate(self, meta: ProblemMeta) -> str:
        """The complete stub file for `meta`, ending with a newline.

        Applies the type mapping and naming rules (`coding_study.domain.naming`); the caller
        writes it to `coding_study.domain.layout.stub_path`. `stub: buggy` problems never reach
        a generator: `cstudy start` copies their buggy file instead.
        """
        ...


@dataclass(frozen=True, slots=True)
class UserCode:
    """Prepare to run the user's file for `meta` (`cstudy test`)."""

    meta: ProblemMeta
    typecheck: bool = False
    """TypeScript only (`cstudy test --typecheck`): also run `tsc --noEmit`; others ignore it."""
    debug: DebugSession | None = None
    """`cstudy test --debug`: launch the runner under the language's debug agent."""


@dataclass(frozen=True, slots=True)
class ReferenceSource:
    approach_id: str
    path: Path
    """The reference file in the problem's `solutions/` directory."""


@dataclass(frozen=True, slots=True)
class References:
    """Materialize these references (`coding_study.domain.layout.reference_build_path`) and
    build them where the language needs it (`cstudy verify`, `cstudy bench`)."""

    meta: ProblemMeta
    sources: tuple[ReferenceSource, ...]


@dataclass(frozen=True, slots=True)
class BenchCode:
    """One runner process for `cstudy bench`: these references, materialized like `References`,
    and the user's file unless `references_only`. TypeScript starts Node with `--expose-gc`."""

    meta: ProblemMeta
    sources: tuple[ReferenceSource, ...]
    references_only: bool = False


type BuildScope = UserCode | References | BenchCode


type ProgressNotice = Callable[[str], None]
"""Prints a line before slow work starts, e.g. "warming Gradle daemon (first run)"."""


@dataclass(frozen=True, slots=True)
class DebugLaunch:
    """A runner whose command starts a debug agent (docs/specs/runners.md#debug-mode).

    `RunnerProcess` waits for the debugger with every time limit off, never restarts the runner,
    and calls `announce` with the session's ready line: once the agent listens, or as the runner
    starts when the session connects to the IDE.
    """

    session: DebugSession
    announce: ProgressNotice
    ready_marker: str = ""
    """Text the runner prints, on standard output or error, once its agent listens."""
    refused_marker: str = ""
    """Text the runner prints when it finds no debugger to connect to, then exits; the session
    connects again for a while."""
    ready_file: Path | None = None
    """For an agent that prints nothing (`debugserver`): a file it writes once it listens.
    `RunnerProcess` creates it empty before each launch."""
    rejected_marker: str = ""
    """Text the agent prints, after it listens, when it refuses the program it was to debug (Delve
    and a Go older than it supports); the session is then a start error that shows the output."""


@dataclass(frozen=True, slots=True)
class DebugServer:
    """The program `cstudy test --debug` starts a compiled runner under."""

    name: str
    """`dlv`, `debugserver` or `lldb-server`."""
    install: str
    """How to install it, as an instruction: "run `xcode-select --install`"."""
    path: Path | None = None
    """None when it is not installed."""


class DebugServers(Protocol):
    """Where the debug servers of Go and Rust are on this machine."""

    def delve(self) -> DebugServer: ...

    def lldb_server(self) -> DebugServer:
        """`debugserver` on macOS, `lldb-server` on Linux."""
        ...


@dataclass(frozen=True, slots=True)
class RunnerLaunch:
    """How to start a runner; `RunnerProcess` appends `--request R --out O`."""

    command: tuple[str, ...]
    cwd: Path
    hello_timeout_ms: int
    """`coding_study.domain.runs.HELLO_TIMEOUT_MS` for the language."""
    debug: DebugLaunch | None = None
    scratch: Path | None = None
    """A directory only this launch uses, such as a private copy of the build output;
    `RunnerProcess` removes it when the run ends, however it ends."""
    environment: Mapping[str, str] = field(default_factory=dict[str, str], hash=False)
    """Variables set for the runner on top of the part of the CLI's own environment that user
    code may inherit (`domain/process_environment.py`); left out of the hash, since a mapping has
    none."""


@dataclass(frozen=True, slots=True)
class Prepared:
    launch: RunnerLaunch
    build_note: str | None = None
    """None when nothing was built; otherwise shown after the build time, e.g. "gradle, warm"."""


@dataclass(frozen=True, slots=True)
class BuildFailed:
    """User or reference code does not compile or type-check (exit code 2)."""

    diagnostics: tuple[str, ...]
    """Compiler lines that mention the file being built, at most 40."""


type PrepareResult = Prepared | BuildFailed


class LanguageRunner(Protocol):
    """One per language: everything language-specific about running code (runners.md)."""

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        """Build what `scope` needs and say how to launch the runner for it.

        Raises RunnerStartError when the toolchain or workspace project is unusable.
        """
        ...


class CaseListener(Protocol):
    """Told of each case as the runner reports it, while the run goes on."""

    def case_started(self, job_id: str, case_id: str) -> None: ...

    def case_finished(self, job_id: str, report: CaseReport) -> None:
        """The case's outcome as recorded: its result, or the hang or crash it ended in. A case
        left not run when restarts run out has none: only the report holds it."""
        ...


class SuiteListener(Protocol):
    """Told of each test of a suite as the runner reports it, while the suite goes on."""

    def test_started(self, test_id: str) -> None: ...

    def test_finished(self, test: SuiteTest) -> None:
        """The test's outcome as recorded: its result, or the hang or crash it ended in."""
        ...


class RunnerProcess(Protocol):
    """Runs any prepared runner; one implementation (`SubprocessRunner`) serves every language."""

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        """One outcome per requested case, including timeouts, crashes and cases not run.
        `listener` hears each case as it starts and ends.

        A launch with a `DebugLaunch` waits for the debugger without time limits or restarts.

        Raises RunnerStartError (exit 4) when the runner does not start and RunnerProtocolError
        (exit 70) when it breaks the protocol.
        """
        ...

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        """Measurements of every target at every size it reached (docs/specs/runners.md#bench-mode).

        A hang or crash stops the target it happened to; the others carry on. Raises like `run`.
        """
        ...

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        """One result per test the framework ran (docs/specs/runners.md#suite-job). `listener`
        hears each test as it starts and ends.

        A test that hangs or crashes is recorded as such, and the suite restarts without the
        tests reported so far. Raises like `run`, and RunnerStartError for a runner without
        suite jobs.
        """
        ...


class ProgressStore(Protocol):
    """progress.db (docs/specs/progress-and-scheduling.md); "most recent" means latest start."""

    def add_attempt(self, attempt: NewAttempt) -> Attempt: ...

    def update_attempt(self, attempt: Attempt) -> None:
        """Store every mutable field of `attempt`."""
        ...

    def active_attempt(self, slug: str | None = None) -> Attempt | None:
        """The most recent `in_progress` attempt, optionally only for `slug`."""
        ...

    def in_progress_attempt(self, slug: str, language: Language | None) -> Attempt | None:
        """`language` None: an attempt at an item that is not autograded."""
        ...

    def latest_attempt(self, slug: str, language: Language | None) -> Attempt | None:
        """The most recent attempt in any status; `language` None for items."""
        ...

    def add_test_run(self, run: RunRecord) -> None: ...

    def latest_test_run(self, attempt_id: int) -> RunRecord | None: ...

    def add_submission(self, submission: SubmissionRecord) -> None: ...

    def submissions(self, attempt_id: int) -> tuple[SubmissionRecord, ...]:
        """A project attempt's submissions, earliest first."""
        ...

    def add_level_unlock(self, unlock: LevelUnlock) -> None:
        """A level opens once: a second unlock of it is ignored."""
        ...

    def level_unlocks(self, attempt_id: int) -> tuple[LevelUnlock, ...]:
        """When each level of a project attempt opened, by level."""
        ...

    def schedule_entry(self, slug: str) -> ScheduleEntry | None: ...

    def save_schedule_entry(self, entry: ScheduleEntry) -> None: ...

    def problem_progress(self) -> Mapping[str, ProblemProgress]:
        """Every slug with at least one attempt or schedule entry."""
        ...

    def finished_attempts(self) -> tuple[Attempt, ...]:
        """Every `passed` or `failed` attempt, earliest end first."""
        ...

    def attempts_in_progress(self) -> tuple[Attempt, ...]:
        """Every `in_progress` attempt, earliest start first."""
        ...

    def add_bench_run(self, run: BenchRunRecord) -> None: ...

    def bench_history(self, slug: str, language: Language) -> tuple[PastRun, ...]:
        """The user's earlier benches of `slug` in `language` (not `--refs-only` ones)."""
        ...

    def latest_bench_outcome(self, attempt_id: int) -> BenchOutcome | None:
        """The verdict of the attempt's most recent bench run; None if it has none."""
        ...

    def latest_bench_verdicts(self) -> tuple[LatestBench, ...]:
        """The latest user bench (not `--refs-only`) of every problem and language, by slug
        and language."""
        ...

    def clear(self) -> None:
        """Deletes every row of progress in one transaction, keeping the database at its schema;
        a failure changes nothing. A later attempt's id stays above every id deleted, since
        `.archive/<slug>/<attempt_id>-<lang>/` may keep their files."""
        ...

    def snapshot(self) -> ProgressSnapshot:
        """Every row of every table but `meta`, as stored (`cstudy export`)."""
        ...

    def restore(self, snapshot: ProgressSnapshot) -> None:
        """Inserts every row, ids included, into a database without progress (`cstudy import`).

        Raises UsageError, and imports nothing, when the database holds progress, the snapshot
        comes from a newer schema, or a table, column or row does not fit.
        """
        ...

    def attempts(self, slug: str) -> tuple[Attempt, ...]:
        """Every attempt at `slug`, in every language and status, latest start first."""
        ...

    def test_runs(self, attempt_id: int) -> tuple[RunRecord, ...]:
        """The attempt's `cstudy test` runs, earliest first."""
        ...

    def bench_runs(self, attempt_id: int) -> tuple[BenchRunSummary, ...]:
        """The attempt's bench runs, earliest first."""
        ...

    def attempt(self, attempt_id: int) -> Attempt | None:
        """The attempt with this id, in any status; None when there is none."""
        ...


class JdkSelector(Protocol):
    """The one JDK Java and Kotlin build and run with: the one the shell selects
    (docs/specs/cli.md#the-selected-jdk)."""

    def selected(self) -> SelectedJdk | None:
        """None when no JDK is found, or when `JAVA_HOME` is set but holds no JDK."""
        ...

    def unusable_java_home(self) -> str | None:
        """`JAVA_HOME` as it is set, when it holds no JDK: nothing is selected then, since the
        selection does not fall back to `PATH`. None otherwise."""
        ...

    def selected_home(self) -> Path | None:
        """The selected JDK's home, with every symbolic link resolved; None when nothing is
        selected."""
        ...


class MachineProbe(Protocol):
    def snapshot(self) -> MachineState:
        """CPU model, power source, load average and core count, right now."""
        ...

    def settle(self, timeout_seconds: float) -> None:
        """Returns once a snapshot shows no environment warning, or after `timeout_seconds`."""
        ...


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware UTC."""
        ...

    def local_date(self, instant: datetime) -> date:
        """The user's calendar date at `instant`."""
        ...

    def monotonic(self) -> float:
        """Seconds from an arbitrary origin, for measuring durations."""
        ...


class ProblemFiles(Protocol):
    """Raw files of the problems in one problems directory, keyed by slug.

    Unlike `ProblemRepository`, it reads directories whose meta.yaml is invalid, so `cstudy verify`
    can report every problem.
    """

    @property
    def directory(self) -> str:
        """Repository-relative, e.g. `problems`."""
        ...

    def slugs(self) -> tuple[str, ...]:
        """The slug of every `<id>-<slug>` directory, in directory order (duplicates kept)."""
        ...

    def directory_names(self) -> tuple[str, ...]:
        """Every `<id>-<slug>` directory name, in the order of `slugs`."""
        ...

    def problem_directory(self, slug: str) -> str:
        """Repository-relative, e.g. `problems/0001-two-sum`, the first directory with this
        slug; raises UnknownProblemError."""
        ...

    def read_text(self, slug: str, name: str) -> str | None:
        """`name` is relative to the problem directory; None when the file does not exist."""
        ...

    def file_names(self, slug: str, directory: str = "") -> tuple[str, ...]:
        """Sorted names of the files (not directories) in a problem subdirectory."""
        ...

    def path(self, slug: str, name: str) -> Path:
        """The absolute path of a file in the problem directory."""
        ...

    def fingerprint(self, slug: str, names: Sequence[str]) -> str:
        """A hash of the names and contents of these files (missing files included)."""
        ...


class InputGenerator(Protocol):
    """A problem's generator.py, loaded in-process (stdlib-only content code)."""

    def generate(self, n: int, seed: int) -> dict[str, JsonValue]:
        """`generate(random.Random(seed), n)` as canonical JSON; raises ContentError on failure."""
        ...

    def validate(self, case_input: Mapping[str, JsonValue]) -> str | None:
        """Why `validate` rejected the input, or None (also when generator.py has none)."""
        ...


class ChangedFiles(Protocol):
    """Version control for `cstudy verify --changed`."""

    def changed_since(self, base: str) -> tuple[str, ...]:
        """Paths relative to the repository root that differ from the merge base with `base`:
        committed on this branch, staged, unstaged, or untracked and not ignored.

        Raises VersionControlError when the comparison is impossible.
        """
        ...


class ProblemTemplates(Protocol):
    """The `cstudy new` templates (docs/specs/cli.md#cstudy-new)."""

    def files(self, template: str) -> Mapping[str, str]:
        """Every file of `template` by its POSIX path in the template, e.g.
        `solutions/explanation.md`."""
        ...


class ContentCode(Protocol):
    def generator(self, path: Path) -> InputGenerator:
        """Raises ContentError when the module cannot be loaded or lacks `generate`."""
        ...

    def checker(self, path: Path) -> Checker:
        """Raises ContentError when the module cannot be loaded or lacks `check`."""
        ...

    def stress_checker(self, path: Path) -> StressChecker:
        """A concurrent problem's stress_checker.py; raises like `checker`."""
        ...


class GeneratedCaseCache(Protocol):
    """`.cs/cases/<slug>/<key>.json`: generated inputs with their expected values."""

    def load(self, slug: str, key: str) -> Mapping[str, GeneratedCase] | None: ...

    def save(self, slug: str, key: str, cases: Mapping[str, GeneratedCase]) -> None: ...


class CalibrationCache(Protocol):
    """`.cs/calibration/<lang>/<slug>.json`: reference timings measured on this machine."""

    def load(self, language: Language, slug: str, key: str) -> Calibration | None:
        """None when nothing is stored for `key` on this machine."""
        ...

    def save(self, language: Language, slug: str, key: str, calibration: Calibration) -> None: ...


class Workspace(Protocol):
    """Files under the repository root, addressed by `coding_study.domain.layout` paths."""

    def exists(self, path: str) -> bool: ...

    def read_text(self, path: str) -> str: ...

    def write_text(self, path: str, text: str) -> None:
        """Creates missing parent directories."""
        ...

    def move_into(self, path: str, directory: str) -> str:
        """Move a file into `directory` (created when missing); returns its new path."""
        ...

    def archive_folder(self, path: str, destination: str) -> None:
        """Move the directory `path` to `destination`, without the untracked entries
        (`workspace_projects.is_untracked`) it holds: those are deleted, and a link is removed,
        never followed. Raises FileExistsError when `destination` exists."""
        ...

    def remove_folder(self, path: str) -> None:
        """Delete the directory `path` with everything in it. A link, there or inside, is
        removed, never followed. Nothing happens when `path` does not exist."""
        ...

    def ensure_link(self, path: str, target: str) -> bool:
        """Make `path` a symbolic link to `target` (relative to the link's directory) when nothing
        is there or a link there dangles; True when it did. Anything else is left alone."""
        ...

    def folder_bytes(self, path: str) -> int:
        """What the files under `path` take, its links not followed; 0 when it is not there."""
        ...

    def content_hash(self, path: str) -> str:
        """sha256 of a file, or of every tracked file under a directory (relative path and bytes,
        in path order; `workspace_projects.is_untracked` entries aside); stable for missing
        paths. A link counts as the text of its target: what it names is never read."""
        ...

    def write_within(self, folder: str, path: str, text: str) -> None:
        """Writes `text` to the file `path`, relative to the directory `folder`, creating missing
        directories on the way; `folder` itself may be a link. The write is atomic: a new file
        beside it replaces the file, keeping its mode; a new file gets mode 0644.

        Raises ValueError, writing nothing, when the file or a directory between `folder` and it
        is a symbolic link, since the write could land outside `folder`, when the file is a
        directory or not a regular file, when a directory on the way is a file, or when `path` is
        not relative and canonical (`project.relative_path_issue`).
        """
        ...

    def locked(self, path: str) -> AbstractContextManager[None]:
        """Holds an exclusive lock on the file `path`, created when missing, for the `with` block:
        another holder, in this process or another, makes it wait. Not reentrant: asking for a
        lock you hold waits forever. A crash never leaves the lock held."""
        ...

    def tracked_files(self, path: str) -> tuple[str, ...]:
        """Every file under the directory `path`, relative to it, in path order, without the
        untracked entries (`workspace_projects.is_untracked`); a link is no file, and is never
        followed. Nothing when `path` is not a directory."""
        ...

    def absolute(self, path: str) -> Path: ...

    def sync_folder(self, path: str, files: Mapping[str, str]) -> None:
        """Makes the tracked files of the directory `path` exactly `files` (text by path,
        relative to it), creating the directory when missing: a file whose content differs is
        written, an equal one keeps its modification time, and any other tracked entry is
        deleted, as is a directory that leaves empty. Untracked entries
        (`workspace_projects.is_untracked`), what build tools wrote, are kept. A link is never
        followed: one at `path`, or among the tracked entries, is removed."""
        ...

    def entries(self, path: str) -> tuple[str, ...]:
        """The names in the directory `path`, links included, in name order; nothing when it is
        not a directory."""
        ...

    def leaving_entry(self, path: str) -> str | None:
        """The first of `path` and what is under it that resolves outside the workspace root,
        through a link on the way to it or a link in it; None when all of it stays inside. A link
        in a directory is read, never followed."""
        ...

    def remove_entry(self, path: str) -> None:
        """Deletes the file or the directory `path` with all it holds. A link is removed, never
        followed. Nothing happens when nothing is there."""
        ...

    def read_within(self, folder: str, path: str) -> bytes:
        """The bytes of the file `path`, relative to the directory `folder`; `folder` itself may
        be a link.

        Raises FileNotFoundError when the file or a directory on the way is missing, and
        ValueError when the file or a directory between `folder` and it is a symbolic link, the
        file is a directory or not a regular file, a directory on the way is a file, or `path` is
        not relative and canonical.
        """
        ...

    def delete_within(self, folder: str, path: str) -> None:
        """Deletes the file `path`, relative to the directory `folder`; `folder` itself may be a
        link. Raises as `read_within` does, deleting nothing."""
        ...

    def move_within(self, folder: str, path: str, target: str) -> None:
        """Moves the file `path` to `target`, both relative to the directory `folder`, creating
        missing directories on the way to `target`; `folder` itself may be a link.

        Raises FileExistsError when anything is at `target`, and otherwise as `read_within` does
        for `path` and `write_within` does for `target`, moving nothing.
        """
        ...

    def locked_with_deadline(self, path: str, deadline_s: float) -> AbstractContextManager[None]:
        """Like `locked`, but waits at most `deadline_s` seconds for another holder to let go,
        then raises LockBusyError."""
        ...


class Toolchains(Protocol):
    """Language adapters for one repository root."""

    def stub_generator(self, language: Language) -> StubGenerator:
        """Raises LanguageNotSetUpError until the language is implemented."""
        ...

    def runner(self, language: Language) -> LanguageRunner:
        """Raises LanguageNotSetUpError until the language is implemented."""
        ...

    def project_test_generator(self, language: Language) -> "ProjectTestGenerator":
        """Raises LanguageNotSetUpError for a language whose project tests are not generated
        yet."""
        ...


class EditorOpener(Protocol):
    def open(self, paths: Sequence[Path]) -> str | None:
        """Run `$VISUAL` or `$EDITOR` on `paths`; None once it ran, else why it could not."""
        ...


class ChangeWatcher(Protocol):
    def changes(self, path: Path) -> Iterator[None]:
        """Yield once per debounced burst of saves to `path` (a file or a directory tree, whose
        untracked entries, `workspace_projects.is_untracked`, are not watched)."""
        ...


class ProjectTestGenerator(Protocol):
    """One per project language (docs/specs/problem-format.md#generated-test-files)."""

    def generate(self, tests: LevelTests) -> str:
        """The native test file of one level, ending with a newline and laid out as the
        language's formatter lays it out; the caller writes it to `tests.path` in the project."""
        ...


@dataclass(frozen=True, slots=True)
class ProjectGrading:
    """Launch the runner for a project's grading job in `root` (`cstudy submit`, and `cstudy
    verify`); a grading job is never debugged."""

    root: Path
    meta: ProblemMeta | None = field(default=None, compare=False)
    """The graded problem, for a runner that compiles the project with its grader (Go, Rust)."""
    level: int | None = field(default=None, compare=False)
    """The graded level: such a runner compiles the methods of levels 1 to it only."""
    release: int | None = None
    """Java and Kotlin: the release level to compile at (`cs.release`) when `root` holds content,
    such as a reference's build; None compiles at the selected JDK's level, as for the user's
    own folder."""
    shared: bool = field(default=False, compare=False)
    """The graded levels have stress cases, so worker threads share the entry class: Rust's
    bridge then calls its methods through `&self` (docs/specs/runners.md#stress-in-project-
    jobs)."""


@dataclass(frozen=True, slots=True)
class ProjectSuite:
    """Launch the runner for a project's native suite in `root` (`cstudy test`, and `cstudy
    verify` D9)."""

    root: Path
    debug: DebugSession | None = None
    """`cstudy test --debug`: breakpoints in the project's code and in its tests both stop."""
    meta: ProblemMeta | None = field(default=None, compare=False)
    """The problem, for a runner whose debug run picks a package of the project (Go)."""
    exclude: tuple[str, ...] = ()
    """The suite job's `exclude`: test files, relative to the root, that a language which compiles
    its tests leaves out of the build, since they may call methods that do not exist yet."""
    release: int | None = None
    """As `ProjectGrading.release`."""


type ProjectScope = ProjectGrading | ProjectSuite


@runtime_checkable
class ProjectRunner(Protocol):
    """A `LanguageRunner` that also runs project jobs (docs/specs/runners.md#project-jobs):
    Python, TypeScript, Java, Kotlin, Go and Rust."""

    def prepare_project(
        self, scope: ProjectScope, notify: ProgressNotice
    ) -> RunnerLaunch | BuildFailed:
        """How to launch the runner in the project root. Python and TypeScript build nothing, and
        any bytecode cached for the project's files is deleted first (runners.md#suite-job); Java
        and Kotlin build the folder first, and BuildFailed holds the compiler's lines when it does
        not compile (runners.md#jvm-project-builds); Rust builds the harness of a grading
        (runners.md#rust-projects), and runs its suites through `ProjectSuiteHost` instead.

        Raises RunnerStartError when the workspace's toolchain lacks what the job needs.
        """
        ...


class ProjectLinks(Protocol):
    """How a workspace's Python project folders reach its venv, and where that venv's console
    scripts think it is (docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace).
    Paths are relative to the workspace `root`."""

    def unlinked(self, root: Path) -> tuple[str, ...]:
        """The Python project folders (`projects/<slug>` with a `pyproject.toml`) whose `.venv`
        link is missing or dangles, in path order."""
        ...

    def relink(self, root: Path) -> tuple[str, ...]:
        """Recreates those links as the relative link to the workspace venv; returns the folders
        it relinked."""
        ...

    def moved_venv(self, root: Path) -> str | None:
        """The venv that the shebangs of `python/.venv`'s console scripts name, when it is not
        this workspace's `python/.venv` (the workspace moved); None when they name it, or when
        there is no script to read."""
        ...


@runtime_checkable
class ProjectTypeChecker(Protocol):
    """A `ProjectRunner` whose language type-checks a project folder as a build step of its own
    (`cstudy test --typecheck`, docs/specs/cli.md#project-problems): TypeScript."""

    def typecheck_project(self, root: Path) -> BuildFailed | None:
        """Every diagnostic in the folder at `root`, with paths relative to the workspace; None
        when it type-checks.

        Raises RunnerStartError when the workspace cannot type-check.
        """
        ...


@runtime_checkable
class ProjectLibraries(Protocol):
    """A runner whose project builds run offline on libraries that `cstudy doctor --fix` caches
    by building a warm-up project (docs/specs/installation-and-workspaces.md#jvm-project-folders):
    Java and Kotlin."""

    def uncached_project_libraries(self) -> str | None:
        """Why a project build would miss a library offline; None when it would find them all."""
        ...


@dataclass(frozen=True, slots=True)
class HostedSuite:
    """A project's native suite, for a `ProjectSuiteHost` to run itself."""

    slug: str
    """The problem, whose build the suite shares with its grading."""
    job: SuiteJob
    debug: DebugSession | None = None
    """`cstudy test --debug`: one test under the language's debug server."""
    listener: SuiteListener | None = None
    """Hears each test as it starts and ends."""


@runtime_checkable
class ProjectSuiteHost(Protocol):
    """A `ProjectRunner` that runs a project's native suite itself, one process per test, instead
    of through a runner process: Rust (docs/specs/runners.md#rust-projects)."""

    def run_project_suite(self, suite: HostedSuite, notify: ProgressNotice) -> SuiteReport:
        """One result per test, in the order they ran; a hang or a crash ends only its test, and
        a test target that does not compile is one `error` result.

        Raises RunnerStartError when the toolchain cannot build or run the suite.
        """
        ...


@dataclass(frozen=True, slots=True)
class FolderCheck:
    """One `cstudy doctor` row about a language's project folders
    (docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace)."""

    name: str
    failing: tuple[str, ...]
    """What fails it, in order: the failing folders, relative to the workspace root, or one
    sentence per problem."""
    problem: str
    """What the row counts: `missing from rust-analyzer.linkedProjects` after a number of
    folders, or `problems`."""
    fix: str | None = None
    """The command that repairs it; None: `cstudy doctor --fix` does."""
    separator: str = ", "
    """Between the failures the row shows: `; ` for sentences, which may hold commas."""


@runtime_checkable
class ProjectFolderChecks(Protocol):
    """A `LanguageRunner` whose project folders reach the workspace's toolchain through files
    `cstudy` writes, or that an editor must be told about: Go and Rust."""

    def folder_checks(self) -> tuple[FolderCheck, ...]:
        """One check per row that applies to this workspace."""
        ...

    def repair_folders(self) -> tuple[str, ...]:
        """Writes what `cstudy doctor --fix` restores in the folders, never over a file;
        returns what it wrote, relative to the workspace root."""
        ...


@dataclass(frozen=True, slots=True)
class ProgressSchema:
    """The schema of progress.db against the one this `cstudy` migrates to
    (docs/specs/progress-and-scheduling.md#schema)."""

    found: int | None
    """The last migration the file records; None before the file exists."""
    latest: int


class ProgressDatabase(Protocol):
    """The progress.db file itself, for `cstudy doctor`; the data goes through `ProgressStore`."""

    def schema(self) -> ProgressSchema:
        """Reads the schema without creating or migrating the file; raises UsageError when the
        file is not a progress database."""
        ...

    def migrate(self) -> None:
        """Brings the file to the latest schema, as the first command to open it would; raises
        UsageError when it cannot."""
        ...


class RunActivity(Protocol):
    """Whether something is running that a reset would pull the files from under."""

    def active_run(self) -> str | None:
        """Says what is active, or None."""
        ...


class EditableConfig(Protocol):
    """The user's `config.toml` as `cstudy config edit` opens it."""

    @property
    def location(self) -> str: ...

    def create_from_template(self) -> bool:
        """Writes the commented template when no file is there; True when it did."""
        ...

    def load(self) -> Config:
        """The defaults for a missing file; raises ConfigError for one that does not load."""
        ...


class ConfigFile(Protocol):
    """The user's `config.toml` as Settings edits it (docs/specs/web-ui.md#settings-view)."""

    @property
    def location(self) -> str: ...

    def read(self) -> ConfigView:
        """A file that is missing, or that does not parse, still reads: it says so."""
        ...

    def apply(self, changes: Mapping[str, object]) -> tuple[str, ...]:
        """Writes each value by the key's dotted name, null removing the key, and returns the
        names of those that changed, keeping everything else in the file. Raises UsageError,
        writing nothing, for a key the file can't take or a value the CLI would refuse, and
        ConfigError, overwriting nothing, for a file that does not parse."""
        ...


@runtime_checkable
class PreferencesStore(Protocol):
    """The web UI's `.cs/serve/preferences.json` (docs/specs/web-ui.md#preferences)."""

    def read(self) -> object:
        """The parsed JSON document; None when the file is missing or unreadable."""
        ...

    def write(self, document: dict[str, object]) -> None:
        """Replaces the whole file."""
        ...


@dataclass(frozen=True, slots=True)
class NotInstalled:
    """The server's package is not in `.cs/lsp/node_modules/`."""


@dataclass(frozen=True, slots=True)
class FileMissing:
    """The package is there, but a workspace file the server needs is not."""

    path: str
    """Relative to the workspace root."""


@dataclass(frozen=True, slots=True)
class VersionPrinted:
    """The server's version command exited 0."""

    output: str
    """Standard output and standard error, combined."""


@dataclass(frozen=True, slots=True)
class VersionFailed:
    """The version command did not run or did not exit 0."""

    reason: str
    """The first line of its standard error, or why it did not start."""


type ServerProbe = NotInstalled | FileMissing | VersionPrinted | VersionFailed


class LanguageServerLocator(Protocol):
    """The servers in the workspace's `.cs/lsp/` (docs/specs/web-ui.md#language-servers)."""

    def probe(self, server: LanguageServer) -> ServerProbe:
        """Whether `.cs/lsp/` holds `server` and what its version command prints."""
        ...


class LanguageServerInstaller(Protocol):
    def install(self) -> ProbeResult | None:
        """Copy the shipped `package.json` and `pnpm-lock.yaml` into `.cs/lsp/` when they differ,
        then run `pnpm install --frozen-lockfile --ignore-scripts` there; None when `pnpm` is
        missing."""
        ...


@dataclass(frozen=True, slots=True)
class WebUiAssets:
    """The page's files that `static/manifest.json` names, as installed."""

    size_bytes: int
    """The total size of the files checked before the first problem."""
    problem: str | None = None
    """The first file in path order that is missing or differs from its digest, such as
    `missing editor.js`; None when every file matches."""


@dataclass(frozen=True, slots=True)
class WebServerLibraries:
    versions: tuple[str, ...]
    """`starlette 1.10.0`, `uvicorn 0.54.0`: each library that imported."""
    problem: str | None = None
    """The first library that does not import, and why."""


class WebUiInstall(Protocol):
    """What `cstudy serve` needs from the installation
    (docs/specs/installation-and-workspaces.md#web-ui-assets)."""

    def assets(self) -> WebUiAssets: ...

    def server_libraries(self) -> WebServerLibraries: ...


class CstudyInstalls(Protocol):
    """The `cstudy` installs on `PATH` and the one that runs
    (docs/specs/cli.md#cstudy-doctor)."""

    def scan(self) -> InstallScan: ...


@dataclass(frozen=True, slots=True)
class ContainerCommand:
    """A command in a running stack's image: `commands.test`, `commands.reset`."""

    command: tuple[str, ...]
    environment: Mapping[str, str]
    """Variables added for this command alone."""
    timeout_s: float
    """A limit of the second clock: the caller starts it once the stack is ready."""
    on_output: Callable[[str], None] | None = None
    """Hears each line as the command prints it."""


class SandboxEngine(Protocol):
    """The container engine that service projects run in (docs/specs/service-projects.md#sandbox).
    Only a service project reaches this: nothing else ever asks the engine anything. Nothing here
    stops the engine, or changes a setting of it, and only what carries `cstudy`'s labels is ever
    removed."""

    def state(self) -> EngineState:
        """Asks and starts nothing: an idle VM stays asleep."""
        ...

    def platform(self) -> str:
        """`sys.platform`, for the messages that differ per platform."""
        ...

    def host_user(self) -> SandboxUser:
        """Who the containers run as, so files in the project folder stay yours."""
        ...

    def owner_pid(self) -> int:
        """The process that answers for the stacks it starts."""
        ...

    def start_engine(self, notify: ProgressNotice) -> None:
        """Starts a stopped engine and waits until it answers.

        Raises SandboxError when it cannot, or may not: `cstudy` never runs `sudo`, and says
        what to run instead.
        """
        ...

    def image_present(self, image: str) -> bool: ...

    def pull(self, image: str, notify: ProgressNotice) -> None:
        """Raises SandboxError when it fails; `notify` hears the progress."""
        ...

    def inventory(self) -> SandboxInventory:
        """Everything that carries `cstudy`'s labels; raises SandboxError when it cannot list."""
        ...

    def is_alive(self, pid: int) -> bool:
        """Whether the process that answers for a stack still runs."""
        ...

    def remove_stack(self, stack: LeftoverStack) -> bool:
        """Takes the whole compose project down, by its name, with no file; False when it could
        not."""
        ...

    def remove_network(self, name: str) -> bool: ...

    def remove_volume(self, name: str) -> bool: ...

    def guard(self, identity: StackIdentity) -> AbstractContextManager[None]:
        """For the `with` block, a process of its own takes the stack down if `cstudy` dies,
        however it dies. Enter it before `start`, and leave it after `stop`."""
        ...

    def start(self, plan: StackPlan, budget: StartupBudget) -> ReadyStack:
        """Writes the stack's files, brings it up and waits for the app's health path. The result
        says when it became ready: the second clock, every limit on a test or a case, starts
        there.

        Raises StackStartError, with the logs read, when it does not become ready within `budget`,
        and SandboxError when the project cannot be mounted. Either way the caller still calls
        `stop`.
        """
        ...

    def stop(self, plan: StackPlan) -> str | None:
        """`down`, with `-v` for a test or a graded stack, and removes the run's folder. What went
        wrong, or None; a stack it could not take down is the next sweep's."""
        ...

    def exec_app(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        """Runs `command` in the running `app` container."""
        ...

    def run_one_off(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        """Runs `command` in a new container of the app's image, on the stack's network."""
        ...

    def restart_app(self, plan: StackPlan, ready: ReadyStack, budget: StartupBudget) -> None:
        """`stop_app`, then `start_app`, for a case that hung the app."""
        ...

    def stop_app(self, plan: StackPlan) -> None:
        """Stops the `app` container and nothing else. Raises StackStartError when it cannot."""
        ...

    def start_app(self, plan: StackPlan, ready: ReadyStack, budget: StartupBudget) -> None:
        """Starts the stopped `app` container; its ports stay, since the forwarder holds them.
        Returns once its health path answers, on the first clock: raises StackStartError when it
        does not."""
        ...

    def app_exit(self, plan: StackPlan, within_ms: int) -> CommandOutcome | None:
        """How the `app` container ended, with its last lines; None if it still runs after waiting
        up to `within_ms`."""
        ...

    def follow_app(self, plan: StackPlan, on_line: Callable[[str], None]) -> None:
        """`on_line` hears each line the app prints, until the `app` container ends."""
        ...

    def probe_egress(self, plan: StackPlan) -> CommandOutcome:
        """From a one-off on `sandbox` alone, tries to reach what no app may: exit 0 when it
        reached none of them, and otherwise names those it did."""
        ...

    def install(
        self, plan: InstallPlan, timeout_s: float, on_output: Callable[[str], None] | None
    ) -> CommandOutcome:
        """Runs the plan's one-off to its end; the caller then calls `stop_install`."""
        ...

    def stop_install(self, plan: InstallPlan) -> str | None:
        """`down`, keeping the install cache; what went wrong, or None."""
        ...


class InstalledPackages(Protocol):
    """What the install holds of cstudy and the software it uses, for `cstudy about`
    (docs/specs/cli.md#cstudy-about)."""

    def own_license_text(self) -> str:
        """The full text of cstudy's own license."""
        ...

    def python_packages(self) -> tuple[Credit, ...]:
        """The installed Python packages cstudy needs to run, with what each declares, by name."""
        ...

    def python_license_texts(self) -> Mapping[str, str]:
        """The license text each of those packages ships, by name; one with none has no entry."""
        ...

    def web_ui_notice(self) -> str | None:
        """`THIRD_PARTY_LICENSES.txt` of the built web page; None when it is not there."""
        ...
