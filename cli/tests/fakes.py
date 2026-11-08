"""In-memory stand-ins for the ports that run code, plus an environment on a temporary root."""

import shutil
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from coding_study.adapters.content_code_loader import ContentCodeLoader
from coding_study.adapters.fs_calibration_cache import FsCalibrationCache
from coding_study.adapters.fs_case_cache import FsGeneratedCaseCache
from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.fs_study_guides import FsStudyGuides
from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.adapters.yaml_problem_sets import YamlProblemSets
from coding_study.application.environment import Environment, ProblemDestination
from coding_study.application.ports import (
    BuildScope,
    CaseListener,
    DebugServer,
    LanguageRunner,
    NotInstalled,
    Prepared,
    PrepareResult,
    ProbeResult,
    ProgressNotice,
    ProjectTestGenerator,
    RunnerLaunch,
    ServerProbe,
    StubGenerator,
    Unpacked,
    VersionPrinted,
)
from coding_study.domain.bench_records import MachineState, PowerSource
from coding_study.domain.cases import FunctionInput
from coding_study.domain.code_intelligence import Archive, GoInstall, LanguageServer
from coding_study.domain.config import Config
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.jdk import JdkSource, SelectedJdk
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import (
    CaseOutcome,
    CaseReport,
    JobReport,
    Returned,
    RunCase,
    RunJob,
    RunnerInfo,
    RunReport,
    RunRequest,
    UserError,
)
from tests.helpers import SCHEMAS_DIRECTORY
from tests.sandbox_fakes import FakeSandbox

NOW = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
FAKE_LAUNCH = RunnerLaunch(("fake-runner",), Path("/"), 1000)
FAKE_PREPARED = Prepared(FAKE_LAUNCH)


class FakeLanguageRunner:
    def __init__(self, result: PrepareResult = FAKE_PREPARED) -> None:
        self.result = result
        self.scopes: list[BuildScope] = []

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        self.scopes.append(scope)
        return self.result


class FakeStubGenerator:
    def generate(self, meta: ProblemMeta) -> str:
        return f"# stub for {meta.slug}\n"


JDK_21 = SelectedJdk("21.0.13", 21, JdkSource.JAVA_HOME)
JDK_HOME = Path("/jdks/selected")


@dataclass
class FakeJdk:
    """The `JdkSelector` of a test: JDK 21 unless the test says otherwise."""

    jdk: SelectedJdk | None = JDK_21
    java_home_without_jdk: str | None = None
    home: Path = JDK_HOME

    def selected(self) -> SelectedJdk | None:
        return self.jdk

    def unusable_java_home(self) -> str | None:
        return self.java_home_without_jdk

    def selected_home(self) -> Path | None:
        return None if self.jdk is None else self.home


def jdk_of(feature: int, source: JdkSource = JdkSource.JAVA_HOME) -> FakeJdk:
    """A selector that selects JDK `feature`."""
    return FakeJdk(SelectedJdk(f"{feature}.0.1", feature, source))


DELVE = DebugServer("dlv", "run `go install dlv`", Path("/go/bin/dlv"))
DEBUGSERVER = DebugServer("debugserver", "run `xcode-select --install`", Path("/xcode/debugserver"))


@dataclass
class FakeDebugServers:
    """Both debug servers installed unless a test says otherwise."""

    delve_server: DebugServer = DELVE
    lldb: DebugServer = DEBUGSERVER

    def delve(self) -> DebugServer:
        return self.delve_server

    def lldb_server(self) -> DebugServer:
        return self.lldb


@dataclass
class FakeToolchains:
    runners: dict[Language, LanguageRunner] = field(default_factory=dict[Language, LanguageRunner])
    stub_generators: dict[Language, StubGenerator] = field(
        default_factory=dict[Language, StubGenerator]
    )
    project_test_generators: dict[Language, ProjectTestGenerator] = field(
        default_factory=dict[Language, ProjectTestGenerator]
    )

    def stub_generator(self, language: Language) -> StubGenerator:
        if language not in self.stub_generators:
            raise LanguageNotSetUpError(language, "stub generator")
        return self.stub_generators[language]

    def project_test_generator(self, language: Language) -> ProjectTestGenerator:
        if language not in self.project_test_generators:
            raise LanguageNotSetUpError(language, "project test generator")
        return self.project_test_generators[language]

    def runner(self, language: Language) -> LanguageRunner:
        if language not in self.runners:
            raise LanguageNotSetUpError(language, "runner")
        return self.runners[language]


type Answer = Callable[[RunJob, RunCase], CaseOutcome]


def two_sum(job: RunJob, case: RunCase) -> Returned:
    """A correct two-sum answer for every case, measured at 1000 ns."""
    assert isinstance(case.input, FunctionInput)
    nums, target = case.input.arguments["nums"], case.input.arguments["target"]
    seen: dict[object, int] = {}
    for index, value in enumerate(nums):  # type: ignore[arg-type]
        if target - value in seen:  # type: ignore[operator]
            return Returned([seen[target - value], index], 1000)  # type: ignore[operator]
        seen[value] = index
    return Returned([], 1000)


class ScriptedRunnerProcess:
    """Answers every case with `answer(job, case)`, telling the listener of each case as a runner
    would; jobs in `load_errors` fail to load."""

    def __init__(self, answer: Answer, load_errors: Mapping[str, UserError] | None = None) -> None:
        self.answer = answer
        self.load_errors = dict(load_errors or {})
        self.requests: list[RunRequest] = []

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        self.requests.append(request)
        jobs = tuple(self._job(job, listener) for job in request.jobs)
        return RunReport(RunnerInfo("fake", 1, "0"), jobs)

    def _job(self, job: RunJob, listener: CaseListener | None) -> JobReport:
        if job.job_id in self.load_errors:
            return JobReport(job.job_id, load_error=self.load_errors[job.job_id])
        reports: list[CaseReport] = []
        for case in job.cases:
            report = CaseReport(case.id, self.answer(job, case))
            if listener is not None:
                listener.case_started(job.job_id, case.id)
                listener.case_finished(job.job_id, report)
            reports.append(report)
        return JobReport(job.job_id, tuple(reports))


class FakeClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now
        self.ticks = 0.0

    def now(self) -> datetime:
        return self.current

    def local_date(self, instant: datetime) -> date:
        return instant.date()

    def monotonic(self) -> float:
        self.ticks += 0.25
        return self.ticks

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class RecordingEditor:
    def __init__(self, result: str | None = None) -> None:
        self.result = result
        self.opened: list[Sequence[Path]] = []

    def open(self, paths: Sequence[Path]) -> str | None:
        self.opened.append(paths)
        return self.result


class FixedChangedFiles:
    """Reports the same changed paths for any base, and records the bases asked for."""

    def __init__(self, *paths: str) -> None:
        self.paths = paths
        self.bases: list[str] = []

    def changed_since(self, base: str) -> tuple[str, ...]:
        self.bases.append(base)
        return self.paths


QUIET_MACHINE = MachineState("Test CPU", PowerSource.AC, 0.5, 8)


@dataclass
class FakeMachine:
    state: MachineState = QUIET_MACHINE
    settled_state: MachineState | None = None
    """What the machine shows once `settle` returns; None leaves `state` as it is."""
    settles: list[float] = field(default_factory=list[float])
    """The timeout of every `settle` call."""

    def snapshot(self) -> MachineState:
        return self.state

    def settle(self, timeout_seconds: float) -> None:
        self.settles.append(timeout_seconds)
        if self.settled_state is not None:
            self.state = self.settled_state


class ScriptedWatcher:
    """Reports `bursts` changes, then stops as if interrupted."""

    def __init__(self, bursts: int = 0) -> None:
        self.bursts = bursts
        self.watched: list[Path] = []

    def changes(self, path: Path) -> Iterator[None]:
        self.watched.append(path)
        for _ in range(self.bursts):
            yield None


def repository_root(tmp_path: Path, problems: Path, tracks: Path | None = None) -> Path:
    """A repository root holding the real schemas, a copy of `problems` and of `tracks`."""
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    shutil.copytree(problems, tmp_path / "problems")
    if tracks is not None:
        shutil.copytree(tracks, tmp_path / "tracks")
    return tmp_path


def declare_jdk(root: Path, directory: str, declaration: str) -> None:
    """Adds `jdk: <declaration>`, such as `{min: 24}`, to a copied problem's meta.yaml."""
    meta = root / "problems" / directory / "meta.yaml"
    meta.write_text(f"{meta.read_text()}jdk: {declaration}\n")


def make_environment(root: Path, **overrides: object) -> Environment:
    """Real file and database adapters on `root`, the workspace and the content root at once;
    fakes for anything that runs code."""
    parts: dict[str, object] = {
        "root": root,
        "content_root": root,
        "config": Config(),
        "problems": FsProblemRepository(root),
        "files": FsProblemFiles(root),
        "progress": SqliteProgressStore(root / "progress.db"),
        "toolchains": FakeToolchains(),
        "jdk": FakeJdk(),
        "runner_process": ScriptedRunnerProcess(lambda job, case: _unanswered(case)),
        "workspace": WorkspaceFs(root),
        "content_code": ContentCodeLoader(root),
        "case_cache": FsGeneratedCaseCache(root),
        "calibrations": FsCalibrationCache(root, "test-machine"),
        "clock": FakeClock(),
        "editor": RecordingEditor(),
        "watcher": ScriptedWatcher(),
        "items": FsItemRepository(root),
        "machine": FakeMachine(),
        "new_problems": ProblemDestination(FsProblemFiles(root), WorkspaceFs(root)),
        "study_guides": FsStudyGuides(None),
        "language_servers": FakeLanguageServers(),
        "sandbox": FakeSandbox(),
        "stack_clients": open_stack_clients,
        "problem_sets": YamlProblemSets(WorkspaceFs(root)),
    }
    parts.update(overrides)
    return Environment(**parts)  # type: ignore[arg-type]


def _unanswered(case: RunCase) -> CaseOutcome:
    raise AssertionError(f"no scripted answer for case {case.id}")


class MemoryPreferences:
    """The web UI's preferences file, in memory."""

    def __init__(self, document: object = None) -> None:
        self.document = document

    def read(self) -> object:
        return self.document

    def write(self, document: dict[str, object]) -> None:
        self.document = document


CODE_INTELLIGENCE_ON = MemoryPreferences({"format": 1, "code_intelligence": True})


PNPM_SUCCEEDED = ProbeResult(0, "")
DOWNLOADED = ProbeResult(0, "")
GO_INSTALLED = ProbeResult(0, "")


class FakeLanguageServers:
    """Locates and installs the servers of the catalog from a table of probes, one per name;
    a server without an entry is not installed. `go` is the selected Go's release."""

    def __init__(
        self,
        probes: Mapping[str, ServerProbe] | None = None,
        installation: ProbeResult | None = PNPM_SUCCEEDED,
        download: ProbeResult = DOWNLOADED,
        go: str | None = "1.27.3",
        go_install: ProbeResult | None = GO_INSTALLED,
    ) -> None:
        self.probes = dict(probes or {})
        self.installation = installation
        self.download_result = download
        self.go = go
        self.go_install_result = go_install
        self.probed: list[str] = []
        self.installs = 0
        self.downloads: list[Archive] = []
        self.go_installs: list[tuple[GoInstall, str]] = []

    def probe(self, server: LanguageServer) -> ServerProbe:
        self.probed.append(server.name)
        return self.probes.get(server.name, NotInstalled())

    def install(self) -> ProbeResult | None:
        self.installs += 1
        return self.installation

    def download(self, archive: Archive) -> ProbeResult:
        self.downloads.append(archive)
        return self.download_result

    def go_release(self) -> str | None:
        return self.go

    def go_install(self, install: GoInstall, version: str) -> ProbeResult | None:
        self.go_installs.append((install, version))
        return self.go_install_result


INSTALLED_SERVERS: Mapping[str, ServerProbe] = {
    "basedpyright": VersionPrinted("basedpyright 1.40.2\nbased on pyright 1.40.2\n"),
    "typescript-language-server": VersionPrinted("6.0.3\n"),
    "jdtls": Unpacked(),
    "gopls": VersionPrinted("golang.org/x/tools/gopls v0.24.0\n"),
    "rust-analyzer": VersionPrinted("rust-analyzer 1.91.0 (f8297e35 2025-10-28)\n"),
}
