"""S18, the virtual clock: declarations and the harness operations of a case
(docs/specs/authoring.md#what-cstudy-verify-checks)."""

from dataclasses import replace

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import Case, Expected, JsonValue, OperationSequence
from coding_study.domain.clock_checks import MAX_ADVANCE_MS, clock_issues
from coding_study.domain.problem import Language
from coding_study.domain.signature import ClassSignature
from coding_study.domain.virtual_clock import ProjectClock
from tests.fakes import repository_root
from tests.helpers import FIXTURE_PROBLEMS, PROJECT_PROBLEMS

DIRECTORY = "problems/0001-bank-project-python"
META = f"{DIRECTORY}/meta.yaml"
TESTS = f"{DIRECTORY}/tests.json"

pytestmark = pytest.mark.usefixtures("graded_clock_runners")


@pytest.fixture(scope="module")
def bank(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PROJECT_PROBLEMS)
    return FsProblemRepository(root).load("bank-project-python")


@pytest.fixture(scope="module")
def lru_cache(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), FIXTURE_PROBLEMS)
    return FsProblemRepository(root).load("lru-cache")


def on_the_virtual_clock(problem, *async_methods: str, language: Language = Language.PYTHON):
    """The bank as a project on the virtual clock whose `async_methods` are asynchronous."""
    signature = problem.meta.signature
    assert isinstance(signature, ClassSignature)
    methods = tuple(
        replace(method, is_async=method.name in async_methods) for method in signature.methods
    )
    meta = replace(
        problem.meta,
        languages=(language,),
        project=replace(problem.meta.project, clock=ProjectClock.VIRTUAL),
        signature=replace(signature, methods=methods),
    )
    return replace(problem, meta=meta)


def with_case(problem, ops, args, level: int = 2):
    """`problem` with one more case, `c1`, holding the operations and no expected values."""
    sequence = OperationSequence(tuple(ops), tuple(map(tuple, args)))
    expected = Expected(list[JsonValue]([None] * len(ops)))
    case = Case("c1", sequence, expected, level=level)
    return replace(problem, cases=(*problem.cases, case))


def case_location(problem) -> str:
    return f"cases[{len(problem.cases) - 1}] c1"


def issues(problem) -> list[str]:
    return [str(issue) for issue in clock_issues(DIRECTORY, problem)]


def case_messages(problem, ops, args, level: int = 2) -> list[str]:
    """The S18 issues of a case on the virtual clock where `deposit` and `transfer` are async."""
    problem = with_case(on_the_virtual_clock(problem, "deposit", "transfer"), ops, args, level)
    return [
        message.removeprefix(f"{TESTS}: {case_location(problem)}: ") for message in issues(problem)
    ]


# the fixture and a complete case


def test_the_bank_on_the_real_clock_has_nothing_to_report(bank):
    assert issues(bank) == []


def test_a_case_that_spawns_waits_and_joins_passes(bank):
    ops = ["Bank", "createAccount", "@spawn", "@advance", "@join", "@now"]
    args = [[], [1, "ivy"], ["t1", "deposit", 2, "ivy", 50], [1000], ["t1"], []]
    assert case_messages(bank, ops, args) == []


def test_a_spawn_may_run_beside_other_tasks(bank):
    ops = ["Bank", "@spawn", "@spawn", "@join", "@join"]
    args = [[], ["a", "deposit", 1, "x", 5], ["b", "deposit", 2, "x", 6], ["b"], ["a"]]
    assert case_messages(bank, ops, args) == []


# a case needs the declared clock


def test_a_project_on_the_real_clock_may_not_use_a_harness_operation(bank):
    problem = with_case(bank, ["Bank", "createAccount", "@now"], [[], [1, "ivy"], []])
    assert issues(problem) == [
        f"{TESTS}: {case_location(problem)}: ops[2]: @now needs project.clock: virtual"
    ]


def test_only_the_first_harness_operation_of_a_case_is_reported(bank):
    problem = with_case(bank, ["Bank", "@advance", "@now"], [[], [5], []])
    assert len(issues(problem)) == 1


def test_a_problem_that_is_no_project_may_not_use_a_harness_operation(lru_cache):
    problem = with_case(lru_cache, ["LRUCache", "@now"], [[2], []], level=1)
    location = f"{TESTS}: {case_location(problem)}"
    assert issues(problem) == [
        f"{location}: ops[1]: @now is a harness operation of project problems"
    ]


def test_a_case_without_harness_operations_needs_no_clock(lru_cache):
    problem = with_case(lru_cache, ["LRUCache", "get"], [[2], [1]], level=1)
    assert issues(problem) == []


def test_a_method_cannot_be_async_in_a_problem_that_is_no_project(lru_cache):
    signature = lru_cache.meta.signature
    assert isinstance(signature, ClassSignature)
    methods = (replace(signature.methods[0], is_async=True), *signature.methods[1:])
    meta = replace(lru_cache.meta, signature=replace(signature, methods=methods))
    assert issues(replace(lru_cache, meta=meta)) == [
        f"{META}: signature.class.methods[0].async: only allowed in project problems"
    ]


# declarations


def test_a_declaration_the_language_cannot_hold_is_reported_at_its_field(bank):
    problem = on_the_virtual_clock(bank, language=Language.JAVA)
    assert issues(problem) == [
        f'{META}: project.clock: "virtual" is for go, python, typescript, kotlin and rust '
        "projects, not java"
    ]


def test_an_async_method_without_the_clock_is_reported_at_the_method(bank):
    signature = bank.meta.signature
    assert isinstance(signature, ClassSignature)
    methods = (signature.methods[0], replace(signature.methods[1], is_async=True))
    meta = replace(bank.meta, signature=replace(signature, methods=methods))
    assert issues(replace(bank, meta=meta)) == [
        f"{META}: signature.class.methods[1].async: "
        "needs project.clock: virtual, since a real clock would wait for real"
    ]


# @advance


@pytest.mark.parametrize("milliseconds", [1, 30000, MAX_ADVANCE_MS])
def test_advance_moves_the_clock_by_a_whole_number_of_milliseconds_in_range(bank, milliseconds):
    assert case_messages(bank, ["Bank", "@advance"], [[], [milliseconds]]) == []


@pytest.mark.parametrize("milliseconds", [0, -1, MAX_ADVANCE_MS + 1])
def test_advance_by_a_duration_out_of_range_is_reported(bank, milliseconds):
    assert case_messages(bank, ["Bank", "@advance"], [[], [milliseconds]]) == [
        f"ops[1]: @advance moves the clock 1 to {MAX_ADVANCE_MS} ms, not {milliseconds}"
    ]


@pytest.mark.parametrize("arguments", [[], ["soon"], [True], [1.5], [1, 2]])
def test_advance_with_arguments_of_the_wrong_shape_is_left_to_s4(bank, arguments):
    assert case_messages(bank, ["Bank", "@advance"], [[], arguments]) == []


# @spawn and @join


def test_a_task_name_cannot_be_spawned_twice(bank):
    ops = ["Bank", "@spawn", "@spawn", "@join"]
    args = [[], ["t", "deposit", 1, "x", 5], ["t", "deposit", 2, "x", 5], ["t"]]
    assert case_messages(bank, ops, args) == ['ops[2]: task "t" is spawned twice']


def test_a_spawned_method_must_be_introduced_by_the_level_of_the_case(bank):
    ops = ["Bank", "@spawn", "@join"]
    args = [[], ["t", "transfer", 1, "x", "y", 5], ["t"]]
    assert case_messages(bank, ops, args, level=1) == ["ops[1]: transfer is introduced at level 2"]


def test_a_spawned_method_of_the_level_of_the_case_passes(bank):
    ops = ["Bank", "@spawn", "@join"]
    args = [[], ["t", "deposit", 1, "x", 5], ["t"]]
    assert case_messages(bank, ops, args, level=1) == []


def test_outside_go_only_an_async_method_is_spawned(bank):
    ops = ["Bank", "@spawn", "@join"]
    args = [[], ["t", "createAccount", 1, "x"], ["t"]]
    assert case_messages(bank, ops, args) == [
        "ops[1]: createAccount is not async, and only go spawns a method that blocks"
    ]


def test_go_spawns_a_method_that_blocks(bank):
    problem = on_the_virtual_clock(bank, language=Language.GO)
    problem = with_case(
        problem,
        ["Bank", "@spawn", "@join"],
        [[], ["t", "createAccount", 1, "x"], ["t"]],
    )
    assert [issue for issue in issues(problem) if "not async" in issue] == []


def test_a_spawn_of_an_unknown_method_is_left_to_s4(bank):
    ops = ["Bank", "@spawn", "@join"]
    assert case_messages(bank, ops, [[], ["t", "evict"], ["t"]]) == []


def test_a_task_is_joined_after_it_is_spawned(bank):
    ops = ["Bank", "@join", "@spawn"]
    args = [[], ["t"], ["t", "deposit", 1, "x", 5]]
    assert case_messages(bank, ops, args) == [
        'ops[1]: task "t" is joined before any @spawn starts it',
        'ops[2]: task "t" is never joined',
    ]


def test_a_task_nobody_spawned_cannot_be_joined(bank):
    assert case_messages(bank, ["Bank", "@join"], [[], ["ghost"]]) == [
        'ops[1]: task "ghost" is joined before any @spawn starts it'
    ]


def test_a_task_is_joined_once(bank):
    ops = ["Bank", "@spawn", "@join", "@join"]
    args = [[], ["t", "deposit", 1, "x", 5], ["t"], ["t"]]
    assert case_messages(bank, ops, args) == ['ops[3]: task "t" is joined twice']


def test_every_spawned_task_is_joined(bank):
    ops = ["Bank", "@spawn", "@spawn", "@join"]
    args = [[], ["a", "deposit", 1, "x", 5], ["b", "deposit", 2, "x", 5], ["b"]]
    assert case_messages(bank, ops, args) == ['ops[1]: task "a" is never joined']


def test_each_unjoined_task_is_reported_at_its_spawn(bank):
    ops = ["Bank", "@spawn", "@spawn"]
    args = [[], ["a", "deposit", 1, "x", 5], ["b", "deposit", 2, "x", 5]]
    assert case_messages(bank, ops, args) == [
        'ops[1]: task "a" is never joined',
        'ops[2]: task "b" is never joined',
    ]


@pytest.mark.parametrize("arguments", [[], ["t"], [4, "deposit"]])
def test_a_spawn_of_the_wrong_shape_is_left_to_s4(bank, arguments):
    assert case_messages(bank, ["Bank", "@spawn"], [[], arguments]) == []
