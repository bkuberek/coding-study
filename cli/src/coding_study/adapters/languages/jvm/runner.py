"""The JVM `LanguageRunner`, shared by Java and Kotlin (docs/specs/runners.md#jvm-build-details).

`prepare` compiles one problem's package through the Gradle daemon (`csClasspath` with
`-Pcs.only=<snake_slug>`), then launches a fresh `java` process on the classpath Gradle wrote.

Each build narrows the project's output directories to its own problem, so concurrent `cstudy`
processes on one workspace would delete each other's classes. Per project and language, one
process at a time writes sources, builds and copies the built classes into a private directory
(`RunClasses`); the JVM loads that copy, which `RunnerProcess` removes when the run ends.

Under `cstudy test --debug` the JVM also gets a JDWP agent that suspends it until the IDE attaches:
listening for the IDE, or, with `--debug-connect`, connecting to an IDE that listens already.
"""

import hashlib
import os
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.debug_port import require_free_port
from coding_study.adapters.languages.jvm.gradle import (
    GradleBuild,
    GradleOutcome,
    compiler_diagnostics,
    output_tail,
)
from coding_study.adapters.languages.jvm.reference_build import REFERENCE_PROJECT, ReferenceBuild
from coding_study.adapters.languages.jvm.run_classes import RUNS_DIRECTORY, RunClasses
from coding_study.adapters.languages.jvm.runtime_jars import RuntimeJars
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    DebugLaunch,
    Prepared,
    PrepareResult,
    ProgressNotice,
    ProjectGrading,
    ProjectScope,
    ProjectSuite,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import (
    BUILD_DIRECTORY,
    JVM_PROJECT,
    reference_build_path,
    watch_path,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import HELLO_TIMEOUT_MS

WORKSPACE = JVM_PROJECT
RUNNERS_BUILD = "jvm"
"""The runners' included build, relative to the runners directory."""
MAIN_CLASS = "cs.runner.Main"
JAVA_EXECUTABLE = "java"
JVM_FLAGS = ("-XX:+UseSerialGC", "-Xshare:auto")
JDWP_LISTENING_MARKER = "Listening for transport dt_socket"
"""JDWP prints this to standard output once it listens for the IDE."""
JDWP_REFUSED_MARKER = "transport error 202: connect failed"
"""JDWP prints this to standard error, then the JVM exits, when no IDE listens to connect to."""
GRADLE_FLAGS = ("-q", "--console=plain")
CLASSPATH_TASK = "csClasspath"
ONLY_PROPERTY = "cs.only"
BUILD_OUTPUT = "build"
"""Under each language's subproject: `classes/` for the JVM, `cs/runtime-classpath.txt` for us."""
CLASSPATH_FILE = f"{BUILD_OUTPUT}/cs/runtime-classpath.txt"
MAIN_CLASSPATH_TASK = "csMainClasspath"
"""A project folder's main classes and runtime classpath (the `cs.project` plugin)."""
SUITE_CLASSPATH_FILE = f"{BUILD_OUTPUT}/cs/test-classpath.txt"
GRADING_CLASSPATH_FILE = f"{BUILD_OUTPUT}/cs/main-classpath.txt"
EXCLUDE_PROPERTY = "cs.exclude"
OFFLINE_FLAG = "--offline"
OFFLINE_MISSING_MARKER = "available for offline mode"
"""Gradle's words for a library its cache lacks in an offline build."""
MISSING_LIBRARIES = "the project build needs libraries that are not cached yet"
PROJECT_SOURCES = "src"
FAILURE_REPORT_MARKER = "* What went wrong:"
FILE_URL = "file://"
PROJECT_LOCK = "project"
WARMUP_PROJECTS = "project-warmup"
"""In the runtime's `jvm/`: a project folder per language that `cstudy doctor --fix` builds."""
WARMUP_CLASSPATH = SUITE_CLASSPATH_FILE
JAR_SUFFIX = ".jar"
LOCK_DIGEST_LENGTH = 12
LOCKS_DIRECTORY = f"{BUILD_DIRECTORY}/jvm-locks"
REFERENCES_LOCK = "references"
PRACTICE_LOCK = "practice"
WAIT_NOTICE = "waiting for another cstudy build in this workspace"
COLD_DAEMON_NOTICE = "warming Gradle daemon (first run)"
WARM_BUILD_NOTE = "gradle, warm"
COLD_BUILD_NOTE = "gradle, cold"


@dataclass(frozen=True, slots=True)
class _GradleProject:
    directory: Path
    selector: tuple[str, ...]
    """Arguments that select the project: none for the workspace, `-p <dir>` otherwise."""
    sources: str
    """Workspace-relative directory of the problem's sources; compiler lines name it."""
    meta: ProblemMeta


@dataclass(frozen=True, slots=True)
class _Compiled:
    classpath: str
    meta: ProblemMeta
    build_note: str


@dataclass(frozen=True, slots=True)
class _Preparation:
    """What one `prepare` call reports to (`notify`) and keeps its private class copies in."""

    notify: ProgressNotice
    classes: RunClasses


class JvmRunner:
    """`LanguageRunner` for one JVM language; both use `cs.runner.Main` from the runners' `jvm/`."""

    def __init__(self, context: LanguageContext, language: Language, gradle: GradleBuild) -> None:
        self._language = language
        self._gradle = gradle
        self._workspace = context.workspace / WORKSPACE
        runners = context.runners / RUNNERS_BUILD
        self._references = ReferenceBuild(context.workspace, self._workspace, runners)
        self._locks = context.workspace / LOCKS_DIRECTORY
        self._runs = context.workspace / RUNS_DIRECTORY
        self._runtime = RuntimeJars(runners, self._locks)

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        """The private class copies belong to the launch, which `RunnerProcess` cleans up; a
        failed preparation never reaches one, so it removes them itself."""
        preparation = _Preparation(notify, RunClasses(self._runs))
        try:
            result = self._prepare(scope, preparation)
        except BaseException:
            preparation.classes.discard()
            raise
        if isinstance(result, BuildFailed):
            preparation.classes.discard()
        return result

    def _prepare(self, scope: BuildScope, preparation: _Preparation) -> PrepareResult:
        match scope:
            case UserCode():
                return self._prepare_user_code(scope, preparation)
            case References():
                compiled = self._build_references(scope.meta, scope.sources, preparation)
                return self._prepared(compiled, preparation)
            case BenchCode():
                return self._prepare_bench(scope, preparation)

    def _prepare_user_code(self, scope: UserCode, preparation: _Preparation) -> PrepareResult:
        """A debug port in use is reported before the build, not after it."""
        debug = _debug_launch(scope.debug, preparation.notify)
        return self._prepared(self._build_user_code(scope.meta, preparation), preparation, debug)

    def _prepare_bench(self, scope: BenchCode, preparation: _Preparation) -> PrepareResult:
        """Both builds on one classpath (`practice.*` and `ref.*` never collide). A reference
        that does not compile is a content error; BuildFailed is always about user code."""
        references = self._build_references(scope.meta, scope.sources, preparation)
        if isinstance(references, BuildFailed):
            raise ContentError(
                [ContentIssue(REFERENCE_PROJECT, "", line) for line in references.diagnostics]
            )
        if scope.references_only:
            return self._prepared(references, preparation)
        user = self._build_user_code(scope.meta, preparation)
        if isinstance(user, BuildFailed):
            return user
        joined = f"{user.classpath}{os.pathsep}{references.classpath}"
        return self._prepared(_Compiled(joined, user.meta, user.build_note), preparation)

    def _build_user_code(
        self, meta: ProblemMeta, preparation: _Preparation
    ) -> "_Compiled | BuildFailed":
        with self._locked(PRACTICE_LOCK, preparation):
            return self._compile(self._user_project(meta), preparation)

    def _build_references(
        self, meta: ProblemMeta, sources: tuple[ReferenceSource, ...], preparation: _Preparation
    ) -> "_Compiled | BuildFailed":
        """Writing the sources, removing the other approaches' files, building and copying the
        classes happen under one lock: no other process builds in between."""
        with self._locked(REFERENCES_LOCK, preparation):
            return self._compile(self._reference_project(meta, sources), preparation)

    def _locked(self, project: str, preparation: _Preparation) -> AbstractContextManager[None]:
        """One lock per Gradle project and language: Java and Kotlin build side by side, while
        the runtime's jars are current (`RuntimeJars`)."""
        path = self._locks / f"{project}-{self._language}.lock"
        return exclusive_lock(path, lambda: preparation.notify(WAIT_NOTICE))

    def _user_project(self, meta: ProblemMeta) -> _GradleProject:
        return _GradleProject(self._workspace, (), watch_path(meta, self._language), meta)

    def _reference_project(
        self, meta: ProblemMeta, sources: tuple[ReferenceSource, ...]
    ) -> _GradleProject:
        self._references.materialize(meta, sources, self._language)
        directory = self._references.project_directory
        problem_sources = _reference_sources(meta, sources, self._language)
        return _GradleProject(directory, ("-p", str(directory)), problem_sources, meta)

    def _compile(
        self, project: _GradleProject, preparation: _Preparation
    ) -> "_Compiled | BuildFailed":
        warm = self._gradle.daemon_running()
        if not warm:
            preparation.notify(COLD_DAEMON_NOTICE)
        task = f":{self._language}:{CLASSPATH_TASK}"
        only = f"-P{ONLY_PROPERTY}={project.meta.snake_slug}"
        with self._runtime.held(lambda: preparation.notify(WAIT_NOTICE)):
            outcome = self._gradle.run([*project.selector, *GRADLE_FLAGS, task, only])
            if outcome.exit_code != 0:
                return _build_failure(outcome, project.sources)
            classpath = self._classpath(project, preparation.classes)
        note = WARM_BUILD_NOTE if warm else COLD_BUILD_NOTE
        return _Compiled(classpath, project.meta, note)

    def _prepared(
        self,
        compiled: "_Compiled | BuildFailed",
        preparation: _Preparation,
        debug: DebugLaunch | None = None,
    ) -> PrepareResult:
        if isinstance(compiled, BuildFailed):
            return compiled
        launch = self._launch(compiled.classpath, self._workspace, preparation, debug)
        return Prepared(launch, compiled.build_note)

    def _launch(
        self,
        classpath: str,
        cwd: Path,
        preparation: _Preparation,
        debug: DebugLaunch | None,
    ) -> RunnerLaunch:
        agent = () if debug is None else (_jdwp_agent(debug.session),)
        return RunnerLaunch(
            (JAVA_EXECUTABLE, *JVM_FLAGS, *agent, "-cp", classpath, MAIN_CLASS),
            cwd,
            HELLO_TIMEOUT_MS[self._language],
            debug,
            preparation.classes.directory,
        )

    def prepare_project(
        self, scope: ProjectScope, notify: ProgressNotice
    ) -> RunnerLaunch | BuildFailed:
        """Builds the project folder with its own Gradle build, then launches the runner in it on
        a private copy of what the build made (docs/specs/runners.md#jvm-project-builds); as in
        `prepare`, a failed preparation removes that copy itself."""
        preparation = _Preparation(notify, RunClasses(self._runs))
        try:
            result = self._prepare_project(scope, preparation)
        except BaseException:
            preparation.classes.discard()
            raise
        if isinstance(result, BuildFailed):
            preparation.classes.discard()
        return result

    def uncached_project_libraries(self) -> str | None:
        """The warm-up project caches what a project folder builds with; while every jar on the
        classpath its build wrote exists, an offline build finds them all. Directories are left
        out: Gradle names resource directories whether or not the build made them."""
        warmup = self._runtime.directory / WARMUP_PROJECTS / self._language
        try:
            classpath = (warmup / WARMUP_CLASSPATH).read_text(encoding="utf-8").strip()
        except OSError:
            return (
                f"the {self._language} warm-up project has not built yet "
                "(it caches what project folders build with)"
            )
        jars = (Path(entry) for entry in classpath.split(os.pathsep) if entry.endswith(JAR_SUFFIX))
        gone = [jar for jar in jars if not jar.exists()]
        if not gone:
            return None
        return (
            f"{len(gone)} libraries the {self._language} warm-up project built with are gone, "
            f"such as {gone[0].name}"
        )

    def _prepare_project(
        self, scope: ProjectScope, preparation: _Preparation
    ) -> RunnerLaunch | BuildFailed:
        """A suite builds the tests too, and may be debugged; grading builds the main classes
        only, so a test file that does not compile never blocks a submission."""
        match scope:
            case ProjectSuite(root=root, debug=session, exclude=exclude):
                debug = _debug_launch(session, preparation.notify)
                build = _ProjectBuild(root, CLASSPATH_TASK, SUITE_CLASSPATH_FILE, exclude)
            case ProjectGrading(root=root):
                debug = None
                build = _ProjectBuild(root, MAIN_CLASSPATH_TASK, GRADING_CLASSPATH_FILE)
        classpath = self._build_project(build, preparation)
        if isinstance(classpath, BuildFailed):
            return classpath
        return self._launch(classpath, build.root, preparation, debug)

    def _build_project(
        self, build: "_ProjectBuild", preparation: _Preparation
    ) -> "str | BuildFailed":
        """One process at a time builds a folder and copies what it built; other folders and
        single-file problems build side by side, while the runtime's jars are current."""
        notify = preparation.notify
        if not self._gradle.daemon_running():
            notify(COLD_DAEMON_NOTICE)
        with (
            exclusive_lock(self._locks / build.lock_name(), lambda: notify(WAIT_NOTICE)),
            self._runtime.held(lambda: notify(WAIT_NOTICE)),
        ):
            outcome = self._gradle.run(build.arguments())
            if outcome.exit_code != 0:
                return _project_build_failure(outcome, build.root)
            return self._project_classpath(build, preparation.classes)

    def _project_classpath(self, build: "_ProjectBuild", classes: RunClasses) -> str:
        path = build.root / build.classpath_file
        try:
            classpath = path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise RunnerStartError(f"gradle did not write the classpath {path}") from error
        return classes.isolate(classpath, (build.root / BUILD_OUTPUT, self._runtime.directory))

    def _classpath(self, project: _GradleProject, classes: RunClasses) -> str:
        """Gradle's runtime classpath, with its build output directories and the runtime's jars
        copied for this run."""
        subproject = project.directory / self._language
        path = subproject / CLASSPATH_FILE
        try:
            classpath = path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise RunnerStartError(f"gradle did not write the runtime classpath {path}") from error
        return classes.isolate(classpath, (subproject / BUILD_OUTPUT, self._runtime.directory))


@dataclass(frozen=True, slots=True)
class _ProjectBuild:
    """One Gradle build of a project folder by the `cs.project` plugin."""

    root: Path
    task: str
    classpath_file: str
    """Relative to the root: what `task` writes."""
    exclude: tuple[str, ...] = ()

    def arguments(self) -> list[str]:
        excluded = [f"-P{EXCLUDE_PROPERTY}={','.join(self.exclude)}"] if self.exclude else []
        return ["-p", str(self.root), *GRADLE_FLAGS, OFFLINE_FLAG, self.task, *excluded]

    def lock_name(self) -> str:
        """Named after the folder, and told apart from a folder of that name elsewhere (a
        reference's copy) by a digest of its absolute path."""
        resolved = str(self.root.resolve())
        digest = hashlib.sha256(resolved.encode()).hexdigest()[:LOCK_DIGEST_LENGTH]
        return f"{PROJECT_LOCK}-{self.root.name}-{digest}.lock"


def _project_build_failure(outcome: GradleOutcome, root: Path) -> BuildFailed:
    """Compiler lines about the folder's sources; libraries missing from Gradle's cache, which
    `cstudy doctor --fix` caches, or any other failure, are environment errors."""
    diagnostics = _project_diagnostics(outcome.output, root)
    if diagnostics:
        return BuildFailed(diagnostics)
    tail = output_tail(outcome.output)
    if OFFLINE_MISSING_MARKER in outcome.output:
        message = f"{MISSING_LIBRARIES}; run `cstudy doctor --fix` once while online"
        raise RunnerStartError(message, tail)
    raise RunnerStartError(f"gradle build failed with exit code {outcome.exit_code}", tail)


def _project_diagnostics(output: str, root: Path) -> tuple[str, ...]:
    """The compiler's lines about the folder's sources, with paths relative to the folder.
    Gradle prints them as the compiler writes them, then again, indented, under its failure
    report: the first copy is kept."""
    printed, _, report = output.partition(FAILURE_REPORT_MARKER)
    for part in (printed, report):
        for folder in dict.fromkeys((str(root.resolve()), str(root))):
            found = compiler_diagnostics(part, f"{folder}/{PROJECT_SOURCES}/")
            if found:
                return tuple(_relative(line, folder) for line in found)
    return ()


def _relative(line: str, folder: str) -> str:
    """javac names a file by its path, kotlinc by its `file://` URL."""
    return line.replace(f"{FILE_URL}{folder}/", "").replace(f"{folder}/", "")


def _debug_launch(session: DebugSession | None, notify: ProgressNotice) -> DebugLaunch | None:
    if session is None:
        return None
    require_free_port(session)
    return DebugLaunch(
        session, notify, ready_marker=JDWP_LISTENING_MARKER, refused_marker=JDWP_REFUSED_MARKER
    )


def _jdwp_agent(session: DebugSession) -> str:
    """Suspended at start until the IDE attaches (`server=y`) or accepts the connection."""
    server = "n" if session.connect else "y"
    return f"-agentlib:jdwp=transport=dt_socket,server={server},suspend=y,address={session.address}"


def _build_failure(outcome: GradleOutcome, sources: str) -> BuildFailed:
    """Compiler errors in the problem's files; any other failure is an environment error."""
    diagnostics = compiler_diagnostics(outcome.output, f"{sources}/")
    if not diagnostics:
        message = f"gradle build failed with exit code {outcome.exit_code}"
        raise RunnerStartError(message, output_tail(outcome.output))
    return BuildFailed(diagnostics)


def _reference_sources(
    meta: ProblemMeta, sources: tuple[ReferenceSource, ...], language: Language
) -> str:
    """The directory above every approach package (`.../ref/<snake_slug>`)."""
    approach_files = (reference_build_path(meta, s.approach_id, language) for s in sources)
    problem_directories = {str(PurePosixPath(path).parents[1]) for path in approach_files}
    return problem_directories.pop() if len(problem_directories) == 1 else REFERENCE_PROJECT
