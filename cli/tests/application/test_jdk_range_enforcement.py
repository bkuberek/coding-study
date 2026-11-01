"""`start`, `test`, `submit` and `bench` refuse a Java or Kotlin problem whose range excludes the
selected JDK, before they write or build anything (docs/specs/cli.md#the-selected-jdk)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.ports import UserCode
from coding_study.application.project_testing import ProjectTestRequest, run_project_tests
from coding_study.application.run_bench import BenchOptions, RunBenchRequest, run_bench
from coding_study.application.run_tests import RunTestsRequest, plan_tests, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, submit_project
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.jdk import JdkSource
from coding_study.domain.problem import Language
from tests.bench_fakes import BENCH_SIZES, optimal_user
from tests.fakes import (
    FakeJdk,
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    declare_jdk,
    jdk_of,
    make_environment,
    two_sum,
)
from tests.fakes import repository_root as copy_repository
from tests.project_fakes import FakeProjectRunner, FakeTestGenerator, ScriptedProjectProcess

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
JVM_PROJECTS = Path(__file__).resolve().parents[1] / "fixtures" / "jvm-projects" / "problems"
JAVA_STUB = "jvm/java/src/main/java/practice/two_sum/Solution.java"
STATEMENT = ".statements/two-sum.md"
FIX = "fix: select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: "
RANGE_26 = "two-sum runs its java version on JDK 21 to 26; "
REFUSALS = [
    pytest.param(
        None,
        jdk_of(27),
        RANGE_26 + "JAVA_HOME selects JDK 27, which cstudy does not support yet",
        id="JDK 27 on a default problem",
    ),
    pytest.param(
        "{min: 24}",
        jdk_of(23),
        "two-sum runs its java version on JDK 24 to 26; JAVA_HOME selects JDK 23, which is too old",
        id="JDK 23 on a min 24 problem",
    ),
    pytest.param(
        "{max: 24}",
        jdk_of(25),
        "two-sum runs its java version on JDK 21 to 24; JAVA_HOME selects JDK 25, "
        "which is newer than the problem supports",
        id="JDK 25 on a max 24 problem",
    ),
    pytest.param(None, FakeJdk(None), RANGE_26 + "no JDK was found", id="no JDK"),
    pytest.param(
        None,
        FakeJdk(None, java_home_without_jdk="/opt/jdk"),
        RANGE_26 + "JAVA_HOME (/opt/jdk) holds no JDK",
        id="a JAVA_HOME without a JDK",
    ),
]


@pytest.fixture
def runner() -> FakeLanguageRunner:
    return FakeLanguageRunner()


def environment_with(tmp_path: Path, runner: FakeLanguageRunner, declared: str | None = None):
    root = copy_repository(tmp_path, PRACTICE)
    if declared is not None:
        declare_jdk(root, "0001-two-sum", declared)
    languages = (Language.PYTHON, Language.JAVA, Language.KOTLIN)
    toolchains = FakeToolchains(
        dict.fromkeys(languages, runner),
        {language: FakeStubGenerator() for language in languages},
    )
    return make_environment(
        root,
        toolchains=toolchains,
        runner_process=ScriptedRunnerProcess(two_sum),
    )


def refused(error: pytest.ExceptionInfo[RunnerStartError]) -> tuple[str, ...]:
    return tuple(str(error.value).splitlines())


def with_jdk(environment, jdk):
    return replace(environment, jdk=jdk)


# start


@pytest.mark.parametrize(("declared", "jdk", "message"), REFUSALS)
def test_start_refuses_a_java_problem_the_jdk_cannot_run(tmp_path, runner, declared, jdk, message):
    environment = with_jdk(environment_with(tmp_path, runner, declared), jdk)
    with pytest.raises(RunnerStartError) as error:
        start_attempt(environment, StartRequest("two-sum", Language.JAVA))
    assert refused(error)[0] == message
    assert refused(error)[1].startswith(FIX)


def test_start_refuses_a_kotlin_problem_the_jdk_cannot_run(tmp_path, runner):
    environment = with_jdk(environment_with(tmp_path, runner), jdk_of(27))
    with pytest.raises(RunnerStartError, match="two-sum runs its kotlin version"):
        start_attempt(environment, StartRequest("two-sum", Language.KOTLIN))


def test_a_refused_start_writes_and_records_nothing(tmp_path, runner):
    environment = with_jdk(environment_with(tmp_path, runner), jdk_of(27))
    with pytest.raises(RunnerStartError):
        start_attempt(environment, StartRequest("two-sum", Language.JAVA))
    assert not environment.workspace.exists(JAVA_STUB)
    assert not environment.workspace.exists(STATEMENT)
    assert environment.progress.in_progress_attempt("two-sum", Language.JAVA) is None


def test_start_refuses_to_resume_an_attempt_the_jdk_can_no_longer_run(tmp_path, runner):
    environment = environment_with(tmp_path, runner)
    start_attempt(environment, StartRequest("two-sum", Language.JAVA))
    with pytest.raises(RunnerStartError):
        start_attempt(with_jdk(environment, jdk_of(27)), StartRequest("two-sum", Language.JAVA))


@pytest.mark.parametrize("jdk", [jdk_of(27), FakeJdk(None)], ids=["JDK 27", "no JDK"])
def test_start_in_python_is_unaffected(tmp_path, runner, jdk):
    environment = with_jdk(environment_with(tmp_path, runner), jdk)
    assert start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt.id


def test_start_accepts_a_problem_that_opts_in_to_the_jdk(tmp_path, runner):
    environment = with_jdk(environment_with(tmp_path, runner, "{max: 27}"), jdk_of(27))
    assert start_attempt(environment, StartRequest("two-sum", Language.JAVA)).attempt.id


def test_start_accepts_a_jdk_of_the_declared_range(tmp_path, runner):
    environment = with_jdk(environment_with(tmp_path, runner, "{min: 24}"), jdk_of(24))
    assert start_attempt(environment, StartRequest("two-sum", Language.JAVA)).attempt.id


# test


@pytest.fixture
def java_attempt(tmp_path, runner):
    """An attempt at two-sum in Java, started on JDK 24, which fits every declared range of these
    tests, and the environment on the JDK that the test selects after it."""

    def started(declared: str | None, jdk):
        environment = environment_with(tmp_path, runner, declared)
        start_attempt(with_jdk(environment, jdk_of(24)), StartRequest("two-sum", Language.JAVA))
        return with_jdk(environment, jdk)

    return started


@pytest.mark.parametrize(("declared", "jdk", "message"), REFUSALS)
def test_test_refuses_before_it_builds(java_attempt, runner, declared, jdk, message):
    environment = java_attempt(declared, jdk)
    with pytest.raises(RunnerStartError) as error:
        run_tests(environment, RunTestsRequest(), lambda _line: None)
    assert refused(error)[0] == message
    assert runner.scopes == []


def test_the_plan_of_a_test_run_refuses_too(java_attempt, runner):
    """The streamed `--events` run plans first, so no event is printed."""
    environment = java_attempt(None, jdk_of(27))
    with pytest.raises(RunnerStartError):
        plan_tests(environment, RunTestsRequest())


def test_test_runs_on_a_jdk_of_the_range(java_attempt, runner):
    environment = java_attempt(None, jdk_of(26, JdkSource.PATH))
    assert run_tests(environment, RunTestsRequest(), lambda _line: None).passed
    assert any(isinstance(scope, UserCode) for scope in runner.scopes)


def test_test_in_python_is_unaffected_by_the_jdk(tmp_path, runner):
    environment = environment_with(tmp_path, runner)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    run = run_tests(with_jdk(environment, FakeJdk(None)), RunTestsRequest(), lambda _line: None)
    assert run.passed


# bench


@pytest.mark.parametrize(("declared", "jdk", "message"), REFUSALS)
def test_bench_refuses_before_it_builds(tmp_path, runner, declared, jdk, message):
    environment = environment_with(tmp_path, runner, declared)
    start_attempt(with_jdk(environment, jdk_of(24)), StartRequest("two-sum", Language.JAVA))
    environment = replace(with_jdk(environment, jdk), runner_process=optimal_user())
    with pytest.raises(RunnerStartError) as error:
        run_bench(
            environment,
            RunBenchRequest(options=BenchOptions(sizes=BENCH_SIZES)),
            lambda _line: None,
        )
    assert refused(error)[0] == message
    assert runner.scopes == []


# project problems


@pytest.fixture
def project_runner() -> FakeProjectRunner:
    return FakeProjectRunner()


def project_environment_on(tmp_path: Path, project_runner: FakeProjectRunner, jdk):
    root = copy_repository(tmp_path, JVM_PROJECTS)
    toolchains = FakeToolchains(
        runners={Language.JAVA: project_runner},
        project_test_generators={Language.JAVA: FakeTestGenerator()},
    )
    environment = make_environment(
        root, toolchains=toolchains, runner_process=ScriptedProjectProcess(), jdk=jdk_of(21)
    )
    return environment, with_jdk(environment, jdk)


PROJECT_RANGE = "bank-project-java runs its java version on JDK 21 to 26; "


def test_start_refuses_a_project_the_jdk_cannot_run(tmp_path, project_runner):
    _, environment = project_environment_on(tmp_path, project_runner, jdk_of(27))
    with pytest.raises(RunnerStartError) as error:
        start_attempt(environment, StartRequest("bank-project-java"))
    assert refused(error)[0] == (
        PROJECT_RANGE + "JAVA_HOME selects JDK 27, which cstudy does not support yet"
    )
    assert not environment.workspace.exists("projects/bank-project-java")


def test_a_project_test_run_refuses_before_it_builds(tmp_path, project_runner):
    started, environment = project_environment_on(tmp_path, project_runner, FakeJdk(None))
    start_attempt(started, StartRequest("bank-project-java"))
    with pytest.raises(RunnerStartError) as error:
        run_project_tests(environment, ProjectTestRequest(), [].append)
    assert refused(error)[0] == PROJECT_RANGE + "no JDK was found"
    assert project_runner.scopes == []


def test_a_submission_refuses_before_it_builds(tmp_path, project_runner):
    started, environment = project_environment_on(tmp_path, project_runner, jdk_of(27))
    start_attempt(started, StartRequest("bank-project-java"))
    with pytest.raises(RunnerStartError):
        submit_project(environment, SubmitRequest(), [].append)
    assert project_runner.scopes == []
