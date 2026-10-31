"""Ports the application drives; adapters implement them (docs/architecture.md)."""

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from coding_study.domain.attempts import Attempt, NewAttempt, RunRecord
from coding_study.domain.bench_records import BenchOutcome, BenchRunRecord, MachineState
from coding_study.domain.bench_runs import BenchReport, BenchRequest
from coding_study.domain.bench_verdict import PastRun
from coding_study.domain.cases import JsonValue
from coding_study.domain.comparators import Checker
from coding_study.domain.config import Config
from coding_study.domain.debugging import DebugSession
from coding_study.domain.generated_cases import GeneratedCase
from coding_study.domain.invariants import StressChecker
from coding_study.domain.items import ItemMeta
from coding_study.domain.problem import Language, Problem, ProblemMeta, ProblemSummary
from coding_study.domain.progress_export import ProgressSnapshot
from coding_study.domain.progress_stats import LatestBench
from coding_study.domain.runs import RunReport, RunRequest
from coding_study.domain.scheduling import ProblemProgress, ScheduleEntry
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
    def run(self, command: Sequence[str], cwd: Path) -> ProbeResult | None:
        """Run a setup command such as `uv sync` to completion, without a time limit; None when
        the executable is missing."""
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


class RunnerProcess(Protocol):
    """Runs any prepared runner; one implementation (`SubprocessRunner`) serves every language."""

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        """One outcome per requested case, including timeouts, crashes and cases not run.

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

    def snapshot(self) -> ProgressSnapshot:
        """Every row of every table but `meta`, as stored (`cstudy export`)."""
        ...

    def restore(self, snapshot: ProgressSnapshot) -> None:
        """Inserts every row, ids included, into a database without progress (`cstudy import`).

        Raises UsageError, and imports nothing, when the database holds progress, the snapshot
        comes from a newer schema, or a table, column or row does not fit.
        """
        ...


class MachineProbe(Protocol):
    def snapshot(self) -> MachineState:
        """CPU model, power source, load average and core count, right now."""
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

    def ensure_link(self, path: str, target: str) -> bool:
        """Make `path` a symbolic link to `target` (relative to the link's directory) when nothing
        is there or a link there dangles; True when it did. Anything else is left alone."""
        ...

    def content_hash(self, path: str) -> str:
        """sha256 of a file, or of every tracked file under a directory (relative path and bytes,
        in path order; `workspace_projects.is_untracked` entries aside); stable for missing
        paths."""
        ...

    def absolute(self, path: str) -> Path: ...


class Toolchains(Protocol):
    """Language adapters for one repository root."""

    def stub_generator(self, language: Language) -> StubGenerator:
        """Raises LanguageNotSetUpError until the language is implemented."""
        ...

    def runner(self, language: Language) -> LanguageRunner:
        """Raises LanguageNotSetUpError until the language is implemented."""
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
