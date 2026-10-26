import os
import socket
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm import create_java_runner, create_kotlin_runner
from coding_study.adapters.languages.jvm.gradle import (
    DaemonRegistry,
    GradleOutcome,
    WrapperGradle,
    compiler_diagnostics,
    wrapper_gradle_version,
)
from coding_study.adapters.languages.jvm.runner import (
    COLD_DAEMON_NOTICE,
    JDWP_LISTENING_MARKER,
    JDWP_REFUSED_MARKER,
    JVM_FLAGS,
    MAIN_CLASS,
    JvmRunner,
)
from coding_study.application.ports import (
    BuildFailed,
    Prepared,
    PrepareResult,
    References,
    ReferenceSource,
    UserCode,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.layout import reference_build_path
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
CLASSPATH = "/classes:/runner.jar"
USER_FILE = "jvm/java/src/main/java/practice/two_sum/Solution.java"
JAVA_SOURCE = "public class Solution {\n}\n"
KOTLIN_SOURCE = "class Solution\n"
WORKSPACE_FILES = (
    "gradle.properties",
    "gradle/libs.versions.toml",
    "java/build.gradle.kts",
    "kotlin/build.gradle.kts",
)
MAX_DIAGNOSTICS = 40


class FakeGradle:
    """Records every build; a successful build writes the classpath file like `csClasspath`."""

    def __init__(self, root: Path, *, warm: bool = True, outcome: GradleOutcome | None = None):
        self.root = root
        self.warm = warm
        self.outcome = outcome or GradleOutcome(0, "")
        self.builds: list[tuple[str, ...]] = []

    def daemon_running(self) -> bool:
        return self.warm

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        self.builds.append(tuple(arguments))
        if self.outcome.exit_code == 0:
            project = self._project_directory(arguments)
            task_project = next(arg for arg in arguments if arg.endswith(":csClasspath"))
            output = project / task_project.split(":")[1] / "build" / "cs" / "runtime-classpath.txt"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(f"{CLASSPATH}\n")
        return self.outcome

    def _project_directory(self, arguments: Sequence[str]) -> Path:
        if "-p" in arguments:
            return Path(arguments[list(arguments).index("-p") + 1])
        return self.root / "jvm"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    workspace = tmp_path / "jvm"
    for relative in WORKSPACE_FILES:
        (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        (workspace / relative).write_text(f"// {relative}\n")
    return tmp_path


def prepare(runner: JvmRunner, scope: UserCode | References) -> tuple[PrepareResult, list[str]]:
    notices: list[str] = []
    return runner.prepare(scope, notices.append), notices


def prepared(result: PrepareResult) -> Prepared:
    assert isinstance(result, Prepared)
    return result


def reference_sources(
    directory: Path, language: Language, *approaches: str
) -> tuple[ReferenceSource, ...]:
    directory.mkdir(parents=True, exist_ok=True)
    extension = "java" if language is Language.JAVA else "kt"
    text = JAVA_SOURCE if language is Language.JAVA else KOTLIN_SOURCE
    sources = []
    for approach in approaches:
        path = directory / f"{approach}.{extension}"
        path.write_text(text)
        sources.append(ReferenceSource(approach, path))
    return tuple(sources)


def compile_failure(*lines: str) -> GradleOutcome:
    return GradleOutcome(1, "\n".join(lines) + "\n")


def test_user_code_builds_only_the_problem_package(root):
    gradle = FakeGradle(root)
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle), UserCode(TWO_SUM)
    )
    assert gradle.builds == [("-q", "--console=plain", ":java:csClasspath", "-Pcs.only=two_sum")]


def test_kotlin_user_code_builds_the_kotlin_project(root):
    gradle = FakeGradle(root)
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.KOTLIN, gradle),
        UserCode(TWO_SUM),
    )
    assert gradle.builds[0][2] == ":kotlin:csClasspath"


def test_launch_runs_main_on_the_built_classpath(root):
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        UserCode(TWO_SUM),
    )
    assert prepared(result).launch.command == ("java", *JVM_FLAGS, "-cp", CLASSPATH, MAIN_CLASS)


def test_launch_starts_in_the_jvm_workspace(root):
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        UserCode(TWO_SUM),
    )
    assert prepared(result).launch.cwd == root / "jvm"


def test_launch_uses_the_jvm_hello_timeout(root):
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.KOTLIN, FakeGradle(root)),
        UserCode(TWO_SUM),
    )
    assert prepared(result).launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.KOTLIN]


def test_jvm_flags_use_the_serial_collector_without_tiering_flags():
    assert JVM_FLAGS == ("-XX:+UseSerialGC", "-Xshare:auto")


def test_cold_daemon_prints_the_warm_up_notice(root):
    _, notices = prepare(
        JvmRunner(
            LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root, warm=False)
        ),
        UserCode(TWO_SUM),
    )
    assert notices == [COLD_DAEMON_NOTICE]


def test_cold_build_is_noted(root):
    result, _ = prepare(
        JvmRunner(
            LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root, warm=False)
        ),
        UserCode(TWO_SUM),
    )
    assert prepared(result).build_note == "gradle, cold"


def test_warm_daemon_prints_nothing(root):
    _, notices = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        UserCode(TWO_SUM),
    )
    assert notices == []


def test_warm_build_is_noted(root):
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        UserCode(TWO_SUM),
    )
    assert prepared(result).build_note == "gradle, warm"


def test_compile_error_in_the_user_file_is_a_build_failure(root):
    error = f"{root}/{USER_FILE}:4: error: ';' expected"
    gradle = FakeGradle(root, outcome=compile_failure(error, "1 error", "FAILURE: Build failed."))
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle), UserCode(TWO_SUM)
    )
    assert result == BuildFailed((error,))


def test_build_failure_keeps_indented_compiler_context(root):
    error = f"{root}/{USER_FILE}:4: error: x"
    gradle = FakeGradle(
        root, outcome=compile_failure(error, "        retur 1;", "        ^", "1 error")
    )
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle), UserCode(TWO_SUM)
    )
    assert result == BuildFailed((error, "        retur 1;", "        ^"))


def test_build_failure_without_user_file_lines_is_an_environment_error(root):
    gradle = FakeGradle(root, outcome=compile_failure("Could not resolve cs:runner."))
    with pytest.raises(RunnerStartError, match="Could not resolve cs:runner"):
        prepare(
            JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle),
            UserCode(TWO_SUM),
        )


def test_references_are_materialized_with_their_package(root, tmp_path):
    sources = reference_sources(tmp_path / "solutions", Language.JAVA, "hash-map")
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        References(TWO_SUM, sources),
    )
    materialized = root / reference_build_path(TWO_SUM, "hash-map", Language.JAVA)
    assert materialized.read_text() == f"package ref.two_sum.hash_map;\n\n{JAVA_SOURCE}"


def test_kotlin_references_get_a_package_without_semicolon(root, tmp_path):
    sources = reference_sources(tmp_path / "solutions", Language.KOTLIN, "brute-force")
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.KOTLIN, FakeGradle(root)),
        References(TWO_SUM, sources),
    )
    materialized = root / reference_build_path(TWO_SUM, "brute-force", Language.KOTLIN)
    assert materialized.read_text() == f"package ref.two_sum.brute_force\n\n{KOTLIN_SOURCE}"


def test_references_drop_approaches_no_longer_requested(root, tmp_path):
    runner = JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root))
    solutions = tmp_path / "solutions"
    prepare(runner, References(TWO_SUM, reference_sources(solutions, Language.JAVA, "a", "b")))
    prepare(runner, References(TWO_SUM, reference_sources(solutions, Language.JAVA, "a")))
    assert not (root / reference_build_path(TWO_SUM, "b", Language.JAVA)).exists()


def test_reference_build_mirrors_the_workspace_build_files(root, tmp_path):
    sources = reference_sources(tmp_path / "solutions", Language.JAVA, "hash-map")
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        References(TWO_SUM, sources),
    )
    build = root / ".cs" / "build" / "jvm"
    assert all((build / relative).read_text() == f"// {relative}\n" for relative in WORKSPACE_FILES)


def test_reference_build_includes_the_runner_build(root, tmp_path):
    sources = reference_sources(tmp_path / "solutions", Language.JAVA, "hash-map")
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        References(TWO_SUM, sources),
    )
    settings = (root / ".cs" / "build" / "jvm" / "settings.gradle.kts").read_text()
    assert 'includeBuild("../../../runners/jvm")' in settings


def test_references_build_the_reference_project(root, tmp_path):
    gradle = FakeGradle(root)
    sources = reference_sources(tmp_path / "solutions", Language.JAVA, "hash-map")
    prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle),
        References(TWO_SUM, sources),
    )
    assert gradle.builds[0][:2] == ("-p", str(root / ".cs" / "build" / "jvm"))


def test_references_launch_on_the_reference_classpath(root, tmp_path):
    sources = reference_sources(tmp_path / "solutions", Language.JAVA, "hash-map")
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        References(TWO_SUM, sources),
    )
    assert CLASSPATH in prepared(result).launch.command


def test_reference_compile_error_is_a_build_failure(root, tmp_path):
    error = (
        f"{root}/.cs/build/jvm/java/src/main/java/ref/two_sum/hash_map/Solution.java:3: error: x"
    )
    gradle = FakeGradle(root, outcome=compile_failure(error))
    sources = reference_sources(tmp_path / "solutions", Language.JAVA, "hash-map")
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle),
        References(TWO_SUM, sources),
    )
    assert result == BuildFailed((error,))


def test_factories_create_jvm_runners(root):
    context = LanguageContext(root, root / "runners")
    runners = (create_java_runner(context), create_kotlin_runner(context))
    assert all(isinstance(runner, JvmRunner) for runner in runners)


def test_missing_wrapper_is_an_environment_error(tmp_path):
    with pytest.raises(RunnerStartError, match="gradlew"):
        WrapperGradle(tmp_path / "jvm", tmp_path / "gradle-home").run(["help"])


def test_wrapper_gradle_reports_exit_code_and_combined_output(tmp_path):
    workspace = tmp_path / "jvm"
    workspace.mkdir(parents=True)
    script = workspace / "gradlew"
    script.write_text(
        f"#!{sys.executable}\nimport sys\n"
        "print('out', flush=True)\nprint('err', file=sys.stderr)\nsys.exit(3)\n"
    )
    script.chmod(0o755)
    outcome = WrapperGradle(workspace, tmp_path / "gradle-home").run(["help"])
    assert outcome == GradleOutcome(3, "out\nerr\n")


def test_diagnostics_keep_only_lines_about_the_source_directory():
    output = "noise\n/abs/src/practice/two_sum/Solution.java:1: error: x\nmore noise\n"
    assert compiler_diagnostics(output, "src/practice/two_sum/") == (
        "/abs/src/practice/two_sum/Solution.java:1: error: x",
    )


def test_diagnostics_are_capped():
    output = "".join(f"e: file:///p/two_sum/S.kt:{line}:1 bad\n" for line in range(60))
    assert len(compiler_diagnostics(output, "/two_sum/")) == MAX_DIAGNOSTICS


def test_wrapper_version_comes_from_the_distribution_url(tmp_path):
    properties = tmp_path / "gradle-wrapper.properties"
    properties.write_text(
        "distributionUrl=https\\://services.gradle.org/distributions/gradle-9.8.2-bin.zip\n"
    )
    assert wrapper_gradle_version(properties) == "9.8.2"


def test_daemon_with_a_live_process_is_running(tmp_path):
    registry = tmp_path / "daemon" / "9.8.2"
    registry.mkdir(parents=True)
    (registry / f"daemon-{os.getpid()}.out.log").write_text("")
    assert DaemonRegistry(tmp_path, "9.8.2").daemon_running()


def test_daemon_log_of_an_ended_process_is_not_running(tmp_path):
    registry = tmp_path / "daemon" / "9.8.2"
    registry.mkdir(parents=True)
    (registry / f"daemon-{2**22 + 12345}.out.log").write_text("")
    assert not DaemonRegistry(tmp_path, "9.8.2").daemon_running()


def test_no_daemon_directory_means_no_daemon(tmp_path):
    assert not DaemonRegistry(tmp_path, "9.8.2").daemon_running()


# `cstudy test --debug`: the JVM starts with a JDWP agent (docs/specs/runners.md#debug-mode).

JDWP = "-agentlib:jdwp=transport=dt_socket,server={server},suspend=y,address=127.0.0.1:{port}"


def debugging(
    root: Path, language: Language, session: DebugSession, notices: list[str] | None = None
) -> tuple[Prepared, FakeGradle]:
    gradle = FakeGradle(root)
    runner = JvmRunner(LanguageContext(root, root / "runners"), language, gradle)
    notify = (notices if notices is not None else []).append
    return prepared(runner.prepare(UserCode(TWO_SUM, debug=session), notify)), gradle


def test_the_jvm_listens_for_the_ide_when_it_waits_for_it(root):
    session = DebugSession(Language.JAVA, 5005)
    launch = debugging(root, Language.JAVA, session)[0].launch
    agent = JDWP.format(server="y", port=5005)
    assert launch.command == ("java", *JVM_FLAGS, agent, "-cp", CLASSPATH, MAIN_CLASS)


def test_the_jvm_connects_to_the_ide_in_connect_mode(root):
    session = DebugSession(Language.JAVA, 5005, connect=True)
    command = debugging(root, Language.JAVA, session)[0].launch.command
    assert JDWP.format(server="n", port=5005) in command


def test_kotlin_uses_the_same_agent(root):
    session = DebugSession(Language.KOTLIN, 6006)
    command = debugging(root, Language.KOTLIN, session)[0].launch.command
    assert JDWP.format(server="y", port=6006) in command


def test_the_jvm_stays_suspended_until_the_ide_resumes_it(root):
    session = DebugSession(Language.JAVA, 5005)
    command = debugging(root, Language.JAVA, session)[0].launch.command
    assert any("suspend=y" in argument for argument in command)


def test_the_launch_asks_for_the_markers_the_agent_prints(root):
    session = DebugSession(Language.JAVA, 5005)
    debug = debugging(root, Language.JAVA, session)[0].launch.debug
    assert debug is not None
    assert (debug.ready_marker, debug.refused_marker) == (
        JDWP_LISTENING_MARKER,
        JDWP_REFUSED_MARKER,
    )


def test_the_markers_are_what_jdwp_prints():
    assert (JDWP_LISTENING_MARKER, JDWP_REFUSED_MARKER) == (
        "Listening for transport dt_socket",
        "transport error 202: connect failed",
    )


def test_the_launch_announces_through_the_notice(root):
    notices: list[str] = []
    debug = debugging(root, Language.JAVA, DebugSession(Language.JAVA, 5005), notices)[
        0
    ].launch.debug
    assert debug is not None
    debug.announce("a line")
    assert notices == ["a line"]


def test_the_launch_carries_the_session(root):
    session = DebugSession(Language.JAVA, 5005, connect=True)
    debug = debugging(root, Language.JAVA, session)[0].launch.debug
    assert debug is not None
    assert debug.session == session


def test_a_normal_launch_has_no_agent(root):
    result, _ = prepare(
        JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, FakeGradle(root)),
        UserCode(TWO_SUM),
    )
    assert prepared(result).launch.debug is None


def test_a_debug_run_is_built_like_any_other(root):
    _, gradle = debugging(root, Language.JAVA, DebugSession(Language.JAVA, 5005))
    assert gradle.builds == [("-q", "--console=plain", ":java:csClasspath", "-Pcs.only=two_sum")]


def test_a_port_in_use_is_reported_before_building(root):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        busy = DebugSession(Language.JAVA, listener.getsockname()[1])
        gradle = FakeGradle(root)
        runner = JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle)
        with pytest.raises(RunnerStartError, match="--debug-port"):
            runner.prepare(UserCode(TWO_SUM, debug=busy), lambda _line: None)
    assert gradle.builds == []


def test_connecting_expects_the_ides_port_to_be_in_use(root):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        ide = DebugSession(Language.JAVA, listener.getsockname()[1], connect=True)
        assert debugging(root, Language.JAVA, ide)[0].launch.debug is not None
