"""`cstudy verify` skips the Java and Kotlin of a problem whose range excludes the selected JDK,
the ready gate counts the skip as not passed, and what it builds from the content compiles at the
problem's minimum release (docs/specs/cli.md#cstudy-verify, docs/specs/runners.md)."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import (
    conformance_repository,
    load_conformance_suite,
)
from coding_study.adapters.environment_factory import conformance_environment
from coding_study.application.project_testing import ProjectTestRequest, run_project_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.verify_conformance import ConformanceRequest, verify_conformance
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.fakes import FakeJdk, FakeToolchains, declare_jdk, jdk_of, make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.project_fakes import (
    FakeProjectRunner,
    FakeTestGenerator,
    ScriptedProjectProcess,
    scripted_builds,
)

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
JVM_PROJECTS = Path(__file__).resolve().parents[1] / "fixtures" / "jvm-projects" / "problems"
CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"
JAVA_PROJECT = "bank-project-java"
CONFORMANCE_JAVA_PROJECT = "conformance-project-java"
SKIPPED_ON_21 = "runs on JDK 24 to 26; JAVA_HOME selects JDK 21"


def verify(environment, slug: str, **fields):
    request = VerifyRequest(slugs=(slug,), **fields)
    [problem] = verify_content(environment, request, lambda _line: None).problems
    return problem


# a single-file problem


@pytest.fixture
def needs_24(tmp_path):
    """Two Sum, whose Java and Kotlin need JDK 24."""
    root = copy_repository(tmp_path, PRACTICE)
    declare_jdk(root, "0001-two-sum", "{min: 24}")
    return root


def on(root, jdk):
    return replace(e2e_environment(root), jdk=jdk)


JVM = pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN], ids=str)


@JVM
def test_verify_skips_the_jvm_languages_outside_the_range(needs_24, language):
    problem = verify(on(needs_24, jdk_of(21)), "two-sum", language=language)
    assert [(r.language, r.skipped) for r in problem.languages] == [(language, SKIPPED_ON_21)]


@JVM
def test_a_skip_alone_does_not_fail_the_problem(needs_24, language):
    assert verify(on(needs_24, jdk_of(21)), "two-sum", language=language).passed


@JVM
def test_a_skipped_language_is_not_covered(needs_24, language):
    problem = verify(on(needs_24, jdk_of(21)), "two-sum", language=language)
    assert not problem.covers(language)


@JVM
def test_the_ready_gate_counts_a_skip_as_not_passed(needs_24, language):
    problem = verify(on(needs_24, jdk_of(21)), "two-sum", language=language, require_ready=True)
    assert f"{language} skipped: {SKIPPED_ON_21}" in problem.ready_errors
    assert not problem.passed


@JVM
def test_without_the_ready_gate_nothing_is_added_for_a_skip(needs_24, language):
    problem = verify(on(needs_24, jdk_of(21)), "two-sum", language=language)
    assert problem.ready_errors == ()


@JVM
def test_no_jdk_skips_the_jvm_languages(needs_24, language):
    problem = verify(on(needs_24, FakeJdk(None)), "two-sum", language=language)
    assert [r.skipped for r in problem.languages] == ["runs on JDK 24 to 26; no JDK was found"]


def test_python_is_never_skipped(needs_24):
    problem = verify(on(needs_24, FakeJdk(None)), "two-sum", language=Language.PYTHON)
    assert [(r.skipped, r.passing) for r in problem.languages] == [(None, 2)]


# a Java project problem


@pytest.fixture
def project(tmp_path):
    root = copy_repository(tmp_path, JVM_PROJECTS)
    runner = FakeProjectRunner()
    toolchains = FakeToolchains(
        runners={Language.JAVA: runner},
        project_test_generators={Language.JAVA: FakeTestGenerator()},
    )
    problem = make_environment(root).problems.load(JAVA_PROJECT)
    environment = make_environment(
        root, toolchains=toolchains, runner_process=scripted_builds(problem), jdk=jdk_of(21)
    )
    return environment, runner


def test_a_java_project_is_skipped_outside_the_range(project):
    environment, runner = project
    problem = verify(replace(environment, jdk=jdk_of(27)), JAVA_PROJECT)
    assert [(r.language, r.skipped) for r in problem.languages] == [
        (Language.JAVA, "runs on JDK 21 to 26; JAVA_HOME selects JDK 27")
    ]
    assert problem.suite is None
    assert runner.scopes == []


def test_the_references_of_a_project_build_at_the_supported_minimum(project):
    environment, runner = project
    verify(environment, JAVA_PROJECT)
    assert {scope.release for scope in runner.scopes} == {21}


def test_the_references_of_a_project_build_at_its_declared_minimum(project):
    environment, runner = project
    declare_jdk(environment.root, "0001-bank-project-java", "{min: 24}")
    verify(replace(environment, jdk=jdk_of(24)), JAVA_PROJECT)
    assert {scope.release for scope in runner.scopes} == {24}


def test_the_users_project_folder_compiles_at_the_jdks_level(project):
    environment, runner = project
    environment = replace(environment, runner_process=ScriptedProjectProcess())
    start_attempt(environment, StartRequest(JAVA_PROJECT))
    run_project_tests(environment, ProjectTestRequest(), [].append)
    assert [scope.release for scope in runner.scopes] == [None]


# a conformance fixture


@pytest.fixture
def conformance_root(tmp_path):
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    (tmp_path / "problems").mkdir()
    fixtures = tmp_path / "runners" / "conformance"
    shutil.copytree(
        CONFORMANCE / f"9026-{CONFORMANCE_JAVA_PROJECT}",
        fixtures / f"9026-{CONFORMANCE_JAVA_PROJECT}",
    )
    expectations = json.loads((CONFORMANCE / "expectations.json").read_text())
    expectations["expectations"] = [
        entry
        for entry in expectations["expectations"]
        if entry["problem"] == CONFORMANCE_JAVA_PROJECT
    ]
    (fixtures / "expectations.json").write_text(json.dumps(expectations))
    return tmp_path


def conformance_on(root, jdk):
    fixtures = conformance_repository(root)
    runner = FakeProjectRunner()
    toolchains = FakeToolchains(
        runners={Language.JAVA: runner},
        project_test_generators={Language.JAVA: FakeTestGenerator()},
    )
    process = scripted_builds(fixtures.load(CONFORMANCE_JAVA_PROJECT))
    environment = conformance_environment(
        make_environment(root, toolchains=toolchains, runner_process=process, jdk=jdk)
    )
    request = ConformanceRequest((CONFORMANCE_JAVA_PROJECT,))
    [result] = verify_conformance(
        environment, load_conformance_suite(root), request, lambda _line: None
    )
    return result, runner


def test_a_conformance_fixture_is_skipped_outside_the_range(conformance_root):
    result, runner = conformance_on(conformance_root, jdk_of(27))
    assert [(r.language, r.skipped) for r in result.languages] == [
        (Language.JAVA, "runs on JDK 21 to 26; JAVA_HOME selects JDK 27")
    ]
    assert result.passed
    assert runner.scopes == []


def test_a_conformance_fixture_builds_at_the_supported_minimum(conformance_root):
    result, runner = conformance_on(conformance_root, jdk_of(26))
    assert result.passed
    assert {scope.release for scope in runner.scopes} == {21}
