from pathlib import Path
from typing import cast

import pytest

from coding_study.application.case_materialization import (
    EXPECTED_VALUES_NOTICE,
    CaseMaterializer,
)
from coding_study.application.ports import BuildFailed, ReferenceSource
from coding_study.domain.cases import Expected, FunctionInput
from coding_study.domain.errors import ContentError
from coding_study.domain.problem import Language
from coding_study.domain.runs import Raised, Returned, UserError
from tests.fakes import (
    FakeLanguageRunner,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
TWO_SUM_DIRECTORY = "problems/0001-two-sum"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, PRACTICE)


@pytest.fixture
def python_runner() -> FakeLanguageRunner:
    return FakeLanguageRunner()


@pytest.fixture
def process() -> ScriptedRunnerProcess:
    return ScriptedRunnerProcess(lambda job, case: Returned([0, 1], 5))


def materialize(root, process, python_runner, slug="two-sum", notices=None):
    environment = make_environment(
        root,
        runner_process=process,
        toolchains=FakeToolchains({Language.PYTHON: python_runner}),
    )
    notify = notices.append if notices is not None else lambda _line: None
    problem = environment.problems.load(slug)
    return CaseMaterializer(environment, notify).runnable_cases(problem)


def test_cases_keep_their_order(root, process, python_runner):
    cases = materialize(root, process, python_runner)
    assert [case.id for case in cases] == ["ex1", "ex2", "h1", "g1"]


def test_hand_written_cases_keep_their_expected_values(root, process, python_runner):
    assert materialize(root, process, python_runner)[2].expected == Expected([0, 3])


def test_generated_cases_are_marked_generated(root, process, python_runner):
    assert materialize(root, process, python_runner)[3].generated


def test_generated_inputs_come_from_the_generator(root, process, python_runner):
    generated = materialize(root, process, python_runner)[3].input
    assert isinstance(generated, FunctionInput)
    assert len(cast(list[int], generated.arguments["nums"])) == 100


def test_generated_expected_values_come_from_the_reference(root, process, python_runner):
    assert materialize(root, process, python_runner)[3].expected == Expected([0, 1])


def test_generated_cases_keep_their_hang_guard(root, process, python_runner):
    assert materialize(root, process, python_runner)[3].hang_guard_ms == 30_000


def test_expected_values_come_from_the_python_expected_from_approach(root, process, python_runner):
    materialize(root, process, python_runner)
    assert python_runner.scopes[0].sources == (
        ReferenceSource("hash-map", root / TWO_SUM_DIRECTORY / "solutions/hash-map.py"),
    )


def test_only_generated_cases_run_the_reference(root, process, python_runner):
    materialize(root, process, python_runner)
    assert [case.id for case in process.requests[0].jobs[0].cases] == ["g1"]


def test_computing_expected_values_is_announced(root, process, python_runner):
    notices: list[str] = []
    materialize(root, process, python_runner, notices=notices)
    assert notices == [EXPECTED_VALUES_NOTICE]


def test_expected_values_are_cached(root, process, python_runner):
    materialize(root, process, python_runner)
    materialize(root, process, python_runner)
    assert len(process.requests) == 1


def test_cached_cases_equal_computed_ones(root, process, python_runner):
    first = materialize(root, process, python_runner)
    assert materialize(root, process, python_runner) == first


def test_changing_the_generator_recomputes(root, process, python_runner):
    materialize(root, process, python_runner)
    generator = root / TWO_SUM_DIRECTORY / "generator.py"
    generator.write_text(generator.read_text() + "\n# changed\n")
    materialize(root, process, python_runner)
    assert len(process.requests) == 2


def test_problems_without_generated_cases_run_nothing(root, process, python_runner):
    materialize(root, process, python_runner, slug="lru-cache")
    assert process.requests == []


def test_reference_failure_is_a_content_error(root, python_runner):
    failing = ScriptedRunnerProcess(lambda job, case: Raised(UserError("KeyError", "3"), 5))
    with pytest.raises(ContentError, match=r"hash-map.*g1.*KeyError: 3"):
        materialize(root, failing, python_runner)


def test_reference_load_error_is_a_content_error(root, python_runner):
    failing = ScriptedRunnerProcess(
        lambda job, case: Returned(1, 1), {"two-sum/hash-map": UserError("SyntaxError", "bad")}
    )
    with pytest.raises(ContentError, match="SyntaxError: bad"):
        materialize(root, failing, python_runner)


def test_reference_build_failure_is_a_content_error(root, process):
    with pytest.raises(ContentError, match="does not build"):
        materialize(root, process, FakeLanguageRunner(BuildFailed(("error",))))


def test_missing_generator_is_a_content_error(root, process, python_runner):
    (root / TWO_SUM_DIRECTORY / "generator.py").unlink()
    with pytest.raises(ContentError, match=r"generator\.py"):
        materialize(root, process, python_runner)


def test_missing_python_expected_source_is_a_content_error(root, process, python_runner):
    (root / TWO_SUM_DIRECTORY / "solutions/hash-map.py").unlink()
    with pytest.raises(ContentError, match="no Python reference"):
        materialize(root, process, python_runner)
