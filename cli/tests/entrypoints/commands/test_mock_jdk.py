"""`cstudy mock` never picks a problem the selected JDK cannot run in the chosen language, and says
why when that leaves nothing (docs/specs/cli.md#cstudy-mock)."""

import pytest
from typer.testing import CliRunner

from coding_study.application.ports import StubGenerator
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import mock
from tests.fakes import (
    FakeJdk,
    FakeStubGenerator,
    FakeToolchains,
    declare_jdk,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_TRACKS, copy_catalog_problems

runner = CliRunner()
SLICE = (
    "0001-two-sum",
    "0002-lru-cache",
    "0003-invert-binary-tree",
    "0007-group-anagrams",
    "0014-first-missing-positive",
)
NOTHING = "no new medium or hard problems in scope"


@pytest.fixture
def root(tmp_path_factory, tmp_path):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), SLICE)
    return repository_root(tmp_path, problems, FIXTURE_TRACKS)


@pytest.fixture
def on_jdk(root, monkeypatch):
    def select(jdk: FakeJdk):
        generators: dict[Language, StubGenerator] = {
            language: FakeStubGenerator() for language in Language
        }
        toolchains = FakeToolchains(stub_generators=generators)
        environment = make_environment(root, toolchains=toolchains, jdk=jdk)
        monkeypatch.setattr(mock, "load_environment", lambda *_: environment)
        return environment

    return select


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["mock", *arguments])


def started(environment) -> list[str]:
    return [attempt.slug for attempt in environment.progress.attempts_in_progress()]


def test_a_jdk_that_cannot_run_java_leaves_no_java_mock(on_jdk):
    environment = on_jdk(jdk_of(27))
    result = invoke("--lang", "java")
    assert result.output.splitlines() == [
        f"{NOTHING}: JDK 27 (JAVA_HOME) cannot run java problems; cstudy supports JDK 21 to 26"
    ]
    assert started(environment) == []


def test_no_jdk_is_named(on_jdk):
    on_jdk(FakeJdk(None))
    assert invoke("--lang", "kotlin").output == (
        f"{NOTHING}: no JDK was found, so kotlin problems cannot run; "
        "cstudy supports JDK 21 to 26\n"
    )


def test_python_mocks_need_no_jdk(on_jdk):
    environment = on_jdk(jdk_of(27))
    invoke()
    assert started(environment) == ["group-anagrams", "lru-cache"]


def test_a_jdk_in_range_starts_the_java_mock_as_before(on_jdk):
    environment = on_jdk(jdk_of(26))
    invoke("--lang", "java")
    assert started(environment) == ["group-anagrams", "lru-cache"]


def test_a_problem_the_jdk_cannot_run_gives_way_to_another(on_jdk, root):
    declare_jdk(root, "0007-group-anagrams", "{min: 24}")
    environment = on_jdk(jdk_of(23))
    invoke("--lang", "java")
    assert started(environment) == ["first-missing-positive", "lru-cache"]


def test_the_same_problem_is_picked_on_a_jdk_of_its_range(on_jdk, root):
    declare_jdk(root, "0007-group-anagrams", "{min: 24}")
    environment = on_jdk(jdk_of(24))
    invoke("--lang", "java")
    assert started(environment) == ["group-anagrams", "lru-cache"]


def test_an_empty_scope_is_not_blamed_on_the_jdk(on_jdk):
    on_jdk(jdk_of(27))
    assert invoke("--track", "practical", "--lang", "java").output == f"{NOTHING}\n"
