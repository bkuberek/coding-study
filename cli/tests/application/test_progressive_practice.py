"""`cstudy start` and `cstudy test` on a progressive problem: levels unlock one at a time."""

from pathlib import Path

import pytest

from coding_study.application.run_tests import RunTestsRequest, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.cases import JsonValue, OperationSequence
from coding_study.domain.errors import UsageError
from coding_study.domain.levels import LevelProgress, LevelRun
from coding_study.domain.problem import Language, Level
from coding_study.domain.runs import CaseOutcome, Raised, Returned, RunCase, RunJob, UserError
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    two_sum,
)
from tests.fakes import repository_root as copy_repository

PHASE4 = Path(__file__).resolve().parents[1] / "fixtures" / "phase4" / "problems"
PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STATEMENT = ".statements/level-store.md"
METHOD_LEVELS = {"put": 1, "get": 1, "remove": 2, "size": 2, "keysWithPrefix": 3}
LEVELS = (Level(1, "Put and get"), Level(2, "Remove and size"), Level(3, "Prefix scans"))


def level_store(implemented: int):
    """A LevelStore answer whose methods above level `implemented` throw "not implemented"."""

    def answer(job: RunJob, case: RunCase) -> CaseOutcome:
        assert isinstance(case.input, OperationSequence)
        values: dict[str, str] = {}
        outputs: list[JsonValue] = [None]
        for index, (op, args) in enumerate(zip(case.input.ops, case.input.args, strict=True)):
            if index == 0:
                continue
            if METHOD_LEVELS[op] > implemented:
                error = UserError("NotImplementedError", "")
                return Raised(error, 1000, op_index=index, partial_output=tuple(outputs))
            outputs.append(_call(values, op, args))
        return Returned(outputs, 1000)

    return answer


def _call(values: dict[str, str], op: str, args: tuple[JsonValue, ...]) -> JsonValue:
    key = str(args[0]) if args else ""
    if op == "put":
        values[key] = str(args[1])
        return None
    if op == "get":
        return values.get(key, "")
    if op == "remove":
        return values.pop(key, None) is not None
    if op == "size":
        return len(values)
    return [stored for stored in sorted(values) if stored.startswith(key)]


def environment_for(tmp_path: Path, implemented: int):
    root = copy_repository(tmp_path, PHASE4)
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    process = ScriptedRunnerProcess(level_store(implemented))
    return make_environment(root, toolchains=toolchains, runner_process=process)


@pytest.fixture
def environment(tmp_path):
    environment = environment_for(tmp_path, implemented=3)
    start_attempt(environment, StartRequest("level-store"))
    return environment


def run(environment, **fields):
    return run_tests(environment, RunTestsRequest(**fields), lambda _line: None)


def statement(environment) -> str:
    return environment.workspace.read_text(STATEMENT)


def unlocked(environment) -> int | None:
    attempt = environment.progress.active_attempt("level-store")
    return attempt.level_unlocked


# cstudy start


def test_start_unlocks_level_1(environment):
    assert unlocked(environment) == 1


def test_start_renders_only_level_1(environment):
    assert "## Level 2" not in statement(environment)


def test_start_reports_the_unlocked_level(tmp_path):
    environment = environment_for(tmp_path, implemented=3)
    started = start_attempt(environment, StartRequest("level-store"))
    assert started.levels == LevelProgress(LEVELS, 1)


def test_start_of_a_problem_without_levels_stores_no_level(tmp_path):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(root, toolchains=toolchains)
    assert start_attempt(environment, StartRequest("two-sum")).attempt.level_unlocked is None


def test_resuming_keeps_the_unlocked_level(environment):
    run(environment)
    start_attempt(environment, StartRequest("level-store"))
    assert "## Level 2: Remove and size" in statement(environment)


def test_a_fresh_attempt_starts_again_at_level_1(environment):
    run(environment)
    started = start_attempt(environment, StartRequest("level-store", fresh=True))
    assert started.attempt.level_unlocked == 1


# cstudy test


def test_runs_only_the_cases_of_unlocked_levels(environment):
    assert [case.id for case in run(environment).cases] == ["ex1", "h1", "h2", "h3"]


def test_passing_every_unlocked_level_unlocks_the_next(environment):
    run(environment)
    assert unlocked(environment) == 2


def test_the_result_reports_the_newly_unlocked_level(environment):
    assert run(environment).levels == LevelRun(1, LevelProgress(LEVELS, 2), newly_unlocked=True)


def test_unlocking_rewrites_the_statement_with_the_new_level(environment):
    run(environment)
    assert "## Level 2: Remove and size" in statement(environment)


def test_unlocking_keeps_later_levels_hidden(environment):
    run(environment)
    assert "Prefix scans" not in statement(environment)


def test_one_run_unlocks_one_level(environment):
    run(environment)
    run(environment)
    assert unlocked(environment) == 3


def test_the_next_run_covers_the_new_level(environment):
    run(environment)
    assert [case.id for case in run(environment).cases][-4:] == ["ex2", "h4", "h5", "h6"]


def test_a_failing_level_unlocks_nothing(tmp_path):
    environment = environment_for(tmp_path, implemented=1)
    start_attempt(environment, StartRequest("level-store"))
    run(environment)
    run(environment)
    assert unlocked(environment) == 2


def test_passing_a_lower_level_unlocks_nothing(environment):
    run(environment)
    run(environment, level=1)
    assert unlocked(environment) == 2


def test_a_requested_level_runs_up_to_it(environment):
    run(environment)
    assert len(run(environment, level=1).cases) == 4


def test_a_passing_case_subset_unlocks_nothing(environment):
    run(environment, case_ids=("ex1", "h1", "h2", "h3"))
    assert unlocked(environment) == 1


def test_a_locked_level_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="level 2 is locked; pass level 1 with cstudy test first"):
        run(environment, level=2)


def test_a_case_of_a_locked_level_is_unknown(environment):
    with pytest.raises(UsageError, match='no case "ex2" in level-store levels 1 to 1'):
        run(environment, case_ids=("ex2",))


def test_partial_levels_are_not_a_full_pass(environment):
    run(environment)
    assert environment.progress.active_attempt().first_pass_at is None


def test_passing_the_last_level_is_a_full_pass(environment):
    for _ in range(3):
        run(environment)
    assert environment.progress.active_attempt().first_pass_at is not None


def test_the_last_level_unlocks_nothing_more(environment):
    for _ in range(3):
        run(environment)
    assert run(environment).levels == LevelRun(3, LevelProgress(LEVELS, 3))


def test_a_level_on_a_problem_without_levels_is_a_usage_error(tmp_path):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    environment = make_environment(
        root, toolchains=toolchains, runner_process=ScriptedRunnerProcess(two_sum)
    )
    start_attempt(environment, StartRequest("two-sum"))
    with pytest.raises(UsageError, match="two-sum has no levels"):
        run(environment, level=1)
