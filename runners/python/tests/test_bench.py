from typing import Any

import pytest

from tests.runner_harness import (
    COUNTER_SIGNATURE,
    COUNTER_SOURCE,
    Event,
    RunnerRun,
    bench_job,
    bench_target,
    run_bench_jobs,
    write_source,
)

ECHO_SOURCE = """
def echo(value):
    return value
"""
SLEEPY_SOURCE = """
import time


def echo(value):
    time.sleep(value / 1000)
    return value
"""
RAISING_SOURCE = """
def echo(value):
    if value > 1:
        raise ValueError("too big")
    return value
"""
STRING_SOURCE = """
def echo(value):
    return "not an int"
"""
ALLOCATING_SOURCE = """
def echo(value):
    return len([index for index in range(value)])
"""
MUTATING_SIGNATURE: dict[str, Any] = {
    "function": {
        "name": "echo",
        "params": [{"name": "value", "type": "int[]"}],
        "returns": {"type": "int"},
    }
}
MUTATING_SOURCE = """
def echo(value):
    if not value:
        raise ValueError("the input was reused after a call emptied it")
    value.clear()
    return 0
"""


def sized(size: int, value: object = None, max_batch: int = 1) -> Event:
    return {
        "size": size,
        "input": {"value": size if value is None else value},
        "max_batch": max_batch,
    }


def ops_sized(size: int) -> Event:
    ops = ["Counter", *(["add"] * size)]
    args: list[list[int]] = [[0], *([[1]] * size)]
    return {"size": size, "ops": ops, "args": args, "max_batch": 1}


def bench(tmp_path, source: str, inputs: list[Event], **settings: Any) -> RunnerRun:
    path = write_source(tmp_path, source)
    return run_bench_jobs(tmp_path, bench_job([bench_target(path, "user")], inputs, **settings))


def samples(run: RunnerRun, target_id: str | None = None) -> list[Event]:
    return [
        event
        for event in run.named("bench_sample")
        if target_id is None or event["target_id"] == target_id
    ]


@pytest.fixture
def echo_file(tmp_path):
    return write_source(tmp_path, ECHO_SOURCE, "echo.py")


def test_a_bench_run_exits_zero(tmp_path):
    assert bench(tmp_path, ECHO_SOURCE, [sized(1)]).exit_code == 0


def test_a_bench_job_is_framed_by_job_start_and_job_end(tmp_path):
    run = bench(tmp_path, ECHO_SOURCE, [sized(1)])
    names = [event["event"] for event in run.events]
    assert (names[1], names[-2], names[-1]) == ("job_start", "job_end", "bye")


def test_every_target_gets_one_sample_per_rep_and_size(tmp_path, echo_file):
    other = write_source(tmp_path, ECHO_SOURCE, "other.py")
    targets = [bench_target(echo_file, "a"), bench_target(other, "b")]
    run = run_bench_jobs(tmp_path, bench_job(targets, [sized(1), sized(2)], reps=3))
    assert len(samples(run, "a")) == len(samples(run, "b")) == 6


def test_targets_take_turns_within_each_rep(tmp_path, echo_file):
    other = write_source(tmp_path, ECHO_SOURCE, "other.py")
    targets = [bench_target(echo_file, "a"), bench_target(other, "b")]
    run = run_bench_jobs(tmp_path, bench_job(targets, [sized(1)], reps=2))
    order = [(event["rep"], event["target_id"]) for event in samples(run)]
    assert order == [(1, "a"), (1, "b"), (2, "a"), (2, "b")]


def test_sizes_run_in_request_order(tmp_path):
    run = bench(tmp_path, ECHO_SOURCE, [sized(1), sized(5)], reps=2)
    assert [event["size"] for event in samples(run)] == [1, 1, 5, 5]


def test_a_sample_reports_wall_and_cpu_time_of_its_calls(tmp_path):
    sample = samples(bench(tmp_path, SLEEPY_SOURCE, [sized(2)], reps=1))[0]
    assert sample["wall_ns"] >= 2_000_000
    assert sample["cpu_ns"] >= 0


def test_an_unbatched_sample_makes_one_call(tmp_path):
    sample = samples(bench(tmp_path, ECHO_SOURCE, [sized(1)], reps=1))[0]
    assert sample["calls"] == 1


def test_fast_calls_are_batched_up_to_the_minimum_sample_duration(tmp_path):
    run = bench(tmp_path, ECHO_SOURCE, [sized(1, max_batch=50)], min_sample_ns=10**9)
    assert {sample["calls"] for sample in samples(run)} == {50}


def test_a_batch_stops_growing_once_samples_last_long_enough(tmp_path):
    run = bench(tmp_path, SLEEPY_SOURCE, [sized(2, max_batch=50)], min_sample_ns=1_000_000)
    assert {sample["calls"] for sample in samples(run)} == {1}


def test_every_call_is_announced_with_bench_start(tmp_path):
    run = bench(tmp_path, ECHO_SOURCE, [sized(1)], reps=2)
    starts = [event for event in run.events if event["event"] == "bench_start"]
    assert starts[0] == {"event": "bench_start", "job_id": "job", "target_id": "user", "size": 1}


def test_the_check_call_and_each_rep_start_separately(tmp_path):
    run = bench(tmp_path, ECHO_SOURCE, [sized(1)], reps=2)
    assert len(run.named("bench_start")) == 3


def test_warmup_runs_until_the_minimum_count(tmp_path):
    warmup = {"min": 3, "max": 3, "cv": 0.05}
    run = bench(tmp_path, ECHO_SOURCE, [sized(1)], reps=2, warmup=warmup)
    assert len(run.named("bench_start")) == 3 + 2


def test_warmup_stops_at_the_maximum_count(tmp_path):
    warmup = {"min": 1, "max": 4, "cv": 0.0}
    run = bench(tmp_path, SLEEPY_SOURCE, [sized(1)], reps=1, warmup=warmup)
    assert len(run.named("bench_start")) == 4 + 1


def test_warmup_stops_once_its_samples_took_the_budget(tmp_path):
    """4 ms calls against a 10 ms budget: at most 3 warmup samples, never the 20 allowed."""
    warmup = {"min": 1, "max": 20, "cv": 0.0}
    run = bench(tmp_path, SLEEPY_SOURCE, [sized(4)], reps=1, warmup=warmup, budget_ms=10)
    assert len(run.named("bench_start")) <= 1 + 3 + 1


def test_a_call_over_the_budget_is_reported_with_its_duration(tmp_path):
    run = bench(tmp_path, SLEEPY_SOURCE, [sized(30)], budget_ms=10)
    exceeded = run.named("bench_budget_exceeded")[0]
    assert (exceeded["size"], exceeded["wall_ns"] >= 30_000_000) == (30, True)


def test_a_target_over_the_budget_is_not_run_at_that_or_larger_sizes(tmp_path):
    run = bench(tmp_path, SLEEPY_SOURCE, [sized(1), sized(30), sized(40)], budget_ms=10)
    assert {sample["size"] for sample in samples(run)} == {1}


def test_a_target_that_raises_reports_bench_error(tmp_path):
    error = bench(tmp_path, RAISING_SOURCE, [sized(1), sized(2)]).named("bench_error")[0]
    assert (error["size"], error["status"], error["error"]["type"]) == (2, "error", "ValueError")


def test_a_target_that_raises_is_dropped(tmp_path):
    run = bench(tmp_path, RAISING_SOURCE, [sized(1), sized(2), sized(3)])
    assert {sample["size"] for sample in samples(run)} == {1}


def test_an_unserializable_result_reports_invalid_output(tmp_path):
    error = bench(tmp_path, STRING_SOURCE, [sized(1)]).named("bench_error")[0]
    assert error["status"] == "invalid_output"


def test_output_targets_report_the_check_call_output(tmp_path, echo_file):
    target = bench_target(echo_file, "user") | {"output": True}
    run = run_bench_jobs(tmp_path, bench_job([target], [sized(4), sized(9)]))
    outputs = [(event["size"], event["output"]) for event in run.named("bench_output")]
    assert outputs == [(4, 4), (9, 9)]


def test_other_targets_report_no_output(tmp_path):
    assert bench(tmp_path, ECHO_SOURCE, [sized(4)]).named("bench_output") == []


def test_a_target_that_does_not_load_reports_load_error(tmp_path, echo_file):
    missing = bench_target(tmp_path / "missing.py", "broken")
    run = run_bench_jobs(tmp_path, bench_job([missing, bench_target(echo_file, "ok")], [sized(1)]))
    error = run.named("load_error")[0]
    assert (error["target_id"], error["error"]["type"]) == ("broken", "FileNotFoundError")


def test_the_other_targets_run_when_one_does_not_load(tmp_path, echo_file):
    missing = bench_target(tmp_path / "missing.py", "broken")
    run = run_bench_jobs(tmp_path, bench_job([missing, bench_target(echo_file, "ok")], [sized(1)]))
    assert {sample["target_id"] for sample in samples(run)} == {"ok"}


def test_every_call_gets_a_fresh_input(tmp_path):
    path = write_source(tmp_path, MUTATING_SOURCE)
    target = bench_target(path, "user", MUTATING_SIGNATURE)
    inputs = [sized(3, value=[1, 2, 3], max_batch=20)]
    job = bench_job([target], inputs, MUTATING_SIGNATURE, min_sample_ns=10**9)
    assert run_bench_jobs(tmp_path, job).named("bench_error") == []


def test_memory_is_measured_with_tracemalloc_per_target_and_size(tmp_path):
    run = bench(tmp_path, ALLOCATING_SOURCE, [sized(10), sized(20)], memory=True)
    measured = [(event["size"], event["metric"]) for event in run.named("bench_memory")]
    assert measured == [(10, "tracemalloc_peak"), (20, "tracemalloc_peak")]


def test_memory_counts_what_the_call_allocates(tmp_path):
    run = bench(tmp_path, ALLOCATING_SOURCE, [sized(100_000)], memory=True)
    assert run.named("bench_memory")[0]["bytes"] >= 100_000 * 8


def test_memory_is_skipped_when_it_is_off(tmp_path):
    assert bench(tmp_path, ALLOCATING_SOURCE, [sized(10)]).named("bench_memory") == []


def test_memory_is_skipped_for_calls_too_slow_to_trace(tmp_path):
    run = bench(tmp_path, SLEEPY_SOURCE, [sized(5)], memory=True, budget_ms=20)
    assert run.named("bench_memory") == []


def test_class_kinds_time_the_whole_operation_sequence(tmp_path):
    path = write_source(tmp_path, COUNTER_SOURCE)
    target = bench_target(path, "user", COUNTER_SIGNATURE) | {"output": True}
    run = run_bench_jobs(tmp_path, bench_job([target], [ops_sized(3)], COUNTER_SIGNATURE))
    assert run.named("bench_output")[0]["output"] == [None, 1, 2, 3]


def test_class_kinds_report_samples(tmp_path):
    path = write_source(tmp_path, COUNTER_SOURCE)
    target = bench_target(path, "user", COUNTER_SIGNATURE)
    run = run_bench_jobs(tmp_path, bench_job([target], [ops_sized(3)], COUNTER_SIGNATURE, reps=2))
    assert len(samples(run)) == 2
