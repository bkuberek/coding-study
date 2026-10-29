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
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    DebugLaunch,
    Prepared,
    PrepareResult,
    ProgressNotice,
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
        """One lock per Gradle project and language: Java and Kotlin build side by side."""
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
        outcome = self._gradle.run([*project.selector, *GRADLE_FLAGS, task, only])
        if outcome.exit_code != 0:
            return _build_failure(outcome, project.sources)
        note = WARM_BUILD_NOTE if warm else COLD_BUILD_NOTE
        return _Compiled(self._classpath(project, preparation.classes), project.meta, note)

    def _prepared(
        self,
        compiled: "_Compiled | BuildFailed",
        preparation: _Preparation,
        debug: DebugLaunch | None = None,
    ) -> PrepareResult:
        if isinstance(compiled, BuildFailed):
            return compiled
        agent = () if debug is None else (_jdwp_agent(debug.session),)
        launch = RunnerLaunch(
            (JAVA_EXECUTABLE, *JVM_FLAGS, *agent, "-cp", compiled.classpath, MAIN_CLASS),
            self._workspace,
            HELLO_TIMEOUT_MS[self._language],
            debug,
            preparation.classes.directory,
        )
        return Prepared(launch, compiled.build_note)

    def _classpath(self, project: _GradleProject, classes: RunClasses) -> str:
        """Gradle's runtime classpath, with its build output directories copied for this run."""
        subproject = project.directory / self._language
        path = subproject / CLASSPATH_FILE
        try:
            classpath = path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise RunnerStartError(f"gradle did not write the runtime classpath {path}") from error
        return classes.isolate(classpath, subproject / BUILD_OUTPUT)


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
