"""The harness operations of a virtual-clock project's cases
(docs/specs/problem-format.md#asynchronous-code-and-the-virtual-clock)."""

import pytest

from coding_study.domain.cases import (
    HarnessOp,
    SpawnedCall,
    is_harness_operation,
    joined_task,
    spawned_call,
)


def test_the_harness_operations_are_the_four_the_format_names():
    assert [operation.value for operation in HarnessOp] == [
        "@advance",
        "@spawn",
        "@join",
        "@now",
    ]


@pytest.mark.parametrize("operation", ["@advance", "@spawn", "@join", "@now", "@enter", "@x"])
def test_an_operation_starting_with_at_is_a_harness_operation(operation):
    assert is_harness_operation(operation)


@pytest.mark.parametrize("operation", ["Bank", "deposit", "advance", "", "a@b"])
def test_any_other_operation_is_a_method(operation):
    assert not is_harness_operation(operation)


def test_a_spawn_names_its_task_its_method_and_the_arguments_of_the_call():
    assert spawned_call(["r1", "receive", 5000, "x"]) == SpawnedCall("r1", "receive", (5000, "x"))


def test_a_spawn_may_call_a_method_without_arguments():
    assert spawned_call(("r1", "size")) == SpawnedCall("r1", "size", ())


@pytest.mark.parametrize(
    "arguments",
    [[], ["r1"], [1, "receive"], ["r1", 2], ["r1", None, 5]],
    ids=["none", "no method", "task not a string", "method not a string", "method is null"],
)
def test_a_malformed_spawn_starts_no_call(arguments):
    assert spawned_call(arguments) is None


def test_a_join_names_the_task_it_waits_for():
    assert joined_task(["r1"]) == "r1"


@pytest.mark.parametrize("arguments", [[], ["r1", "r2"], [3], [None]])
def test_a_malformed_join_waits_for_no_task(arguments):
    assert joined_task(arguments) is None
