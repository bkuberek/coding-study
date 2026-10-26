"""The JVM `LanguageRunner`, shared by Java and Kotlin (docs/specs/runners.md#jvm-build-details).

`prepare` compiles one problem's package through the Gradle daemon (`csClasspath` with
`-Pcs.only=<snake_slug>`), then launches a fresh `java` process on the classpath Gradle wrote.
"""

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm.gradle import (
    GradleBuild,
    GradleOutcome,
    compiler_diagnostics,
    output_tail,
)
from coding_study.adapters.languages.jvm.reference_build import REFERENCE_PROJECT, ReferenceBuild
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    Prepared,
    PrepareResult,
    ProgressNotice,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import JVM_PROJECT, reference_build_path, watch_path
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import HELLO_TIMEOUT_MS

WORKSPACE = JVM_PROJECT
RUNNERS_BUILD = "jvm"
"""The runners' included build, relative to the runners directory."""
MAIN_CLASS = "cs.runner.Main"
JAVA_EXECUTABLE = "java"
JVM_FLAGS = ("-XX:+UseSerialGC", "-Xshare:auto")
GRADLE_FLAGS = ("-q", "--console=plain")
CLASSPATH_TASK = "csClasspath"
ONLY_PROPERTY = "cs.only"
CLASSPATH_FILE = "build/cs/runtime-classpath.txt"
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


class JvmRunner:
    """`LanguageRunner` for one JVM language; both use `cs.runner.Main` from the runners' `jvm/`."""

    def __init__(self, context: LanguageContext, language: Language, gradle: GradleBuild) -> None:
        self._language = language
        self._gradle = gradle
        self._workspace = context.workspace / WORKSPACE
        runners = context.runners / RUNNERS_BUILD
        self._references = ReferenceBuild(context.workspace, self._workspace, runners)

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        match scope:
            case UserCode():
                return self._prepared(self._compile(self._user_project(scope.meta), notify))
            case References():
                project = self._reference_project(scope.meta, scope.sources)
                return self._prepared(self._compile(project, notify))
            case BenchCode():
                return self._prepare_bench(scope, notify)

    def _prepare_bench(self, scope: BenchCode, notify: ProgressNotice) -> PrepareResult:
        """Both builds on one classpath (`practice.*` and `ref.*` never collide). A reference
        that does not compile is a content error; BuildFailed is always about user code."""
        references = self._compile(self._reference_project(scope.meta, scope.sources), notify)
        if isinstance(references, BuildFailed):
            raise ContentError(
                [ContentIssue(REFERENCE_PROJECT, "", line) for line in references.diagnostics]
            )
        if scope.references_only:
            return self._prepared(references)
        user = self._compile(self._user_project(scope.meta), notify)
        if isinstance(user, BuildFailed):
            return user
        joined = f"{user.classpath}{os.pathsep}{references.classpath}"
        return self._prepared(_Compiled(joined, user.meta, user.build_note))

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
        self, project: _GradleProject, notify: ProgressNotice
    ) -> "_Compiled | BuildFailed":
        warm = self._gradle.daemon_running()
        if not warm:
            notify(COLD_DAEMON_NOTICE)
        task = f":{self._language}:{CLASSPATH_TASK}"
        only = f"-P{ONLY_PROPERTY}={project.meta.snake_slug}"
        outcome = self._gradle.run([*project.selector, *GRADLE_FLAGS, task, only])
        if outcome.exit_code != 0:
            return _build_failure(outcome, project.sources)
        note = WARM_BUILD_NOTE if warm else COLD_BUILD_NOTE
        return _Compiled(self._classpath(project), project.meta, note)

    def _prepared(self, compiled: "_Compiled | BuildFailed") -> PrepareResult:
        if isinstance(compiled, BuildFailed):
            return compiled
        launch = RunnerLaunch(
            (JAVA_EXECUTABLE, *JVM_FLAGS, "-cp", compiled.classpath, MAIN_CLASS),
            self._workspace,
            HELLO_TIMEOUT_MS[self._language],
        )
        return Prepared(launch, compiled.build_note)

    def _classpath(self, project: _GradleProject) -> str:
        path = project.directory / self._language / CLASSPATH_FILE
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise RunnerStartError(f"gradle did not write the runtime classpath {path}") from error


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
