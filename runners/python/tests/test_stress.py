"""Concurrent jobs end to end through `main` (docs/specs/runners.md#concurrent-jobs)."""

import json
from pathlib import Path
from typing import Any

import pytest

from cs_runner.program import BAD_REQUEST_EXIT_CODE, RESTART_EXIT_CODE
from tests.runner_harness import Event, RunnerRun, request_of, run_request_text, write_source

COUNTER_SIGNATURE: dict[str, Any] = {
    "class": {
        "name": "Counter",
        "constructor": {"params": []},
        "methods": [
            {"name": "increment", "params": [], "returns": {"type": "void"}},
            {"name": "get", "params": [], "returns": {"type": "int"}},
            {"name": "wait", "params": [], "returns": {"type": "void"}, "blocking": True},
            {"name": "fail", "params": [{"name": "at", "type": "int"}], "returns": {"type": "int"}},
        ],
    }
}
LOCKED = """
import threading


class Counter:
    def __init__(self):
        self._lock = threading.Lock()
        self._count = 0
        self._never = threading.Event()

    def increment(self):
        with self._lock:
            count = self._count
            self._count = count + 1

    def get(self):
        return self._count

    def wait(self):
        self._never.wait()

    def fail(self, at):
        if at == 3:
            raise IndexError("failed at 3")
        return at
"""
RACY = LOCKED.replace(
    "        with self._lock:\n            count", "        if True:\n            count"
)
ASYNC = """
import asyncio


class Counter:
    def __init__(self):
        self._count = 0
        self._never = asyncio.Event()

    def increment(self):
        self._count += 1

    def get(self):
        return self._count

    async def wait(self):
        await self._never.wait()

    async def fail(self, at):
        await asyncio.sleep(0)
        count = self._count
        await asyncio.sleep(0)
        self._count = count + at
        return self._count
"""
PERTURB = {"yield_probability": 0.05, "max_yields": 3, "python_granularity": "line"}


def script(*ops: tuple[str, list[Any]]) -> dict[str, Any]:
    return {"ops": [op for op, _ in ops], "args": [args for _, args in ops]}


def stress_case(
    case_id: str, workers: list[dict[str, Any]], seed: int = 1, **perturb: Any
) -> Event:
    return {
        "id": case_id,
        "stress": {
            "seed": seed,
            "deadline_ms": 1000,
            "perturb": PERTURB | perturb,
            "setup": script(("Counter", [])),
            "workers": workers,
            "final": script(("get", [])),
        },
    }


def increments(count: int) -> dict[str, Any]:
    return script(*[("increment", [])] * count)


def concurrent_job(path: Path, cases: list[Event], model: str = "threads") -> Event:
    methods = {method["name"]: method["name"] for method in COUNTER_SIGNATURE["class"]["methods"]}
    return {
        "job_id": "job",
        "kind": "concurrent",
        "model": model,
        "target": {"path": str(path)},
        "names": {"class": "Counter", "methods": methods},
        "signature": COUNTER_SIGNATURE,
        "cases": cases,
    }


def run(directory: Path, source: str, cases: list[Event], model: str = "threads") -> RunnerRun:
    path = write_source(directory, source)
    return run_request_text(directory, json.dumps(request_of(concurrent_job(path, cases, model))))


def test_hello_announces_the_stress_feature(tmp_path):
    hello = run(tmp_path, LOCKED, []).events[0]
    assert hello["features"] == ["stress"]


def test_a_locked_counter_counts_every_increment(tmp_path):
    result = run(tmp_path, LOCKED, [stress_case("s", [increments(300)] * 4)]).only_result()
    assert (result["status"], result["output"]["final"]) == ("ok", [1200])


def test_a_stress_result_has_one_output_per_op(tmp_path):
    result = run(tmp_path, LOCKED, [stress_case("s", [increments(2), increments(1)])]).only_result()
    assert result["output"] == {"setup": [None], "workers": [[None, None], [None]], "final": [3]}


def test_injected_yields_expose_a_racy_counter(tmp_path):
    case = stress_case("s", [increments(300)] * 4, yield_probability=0.5)
    result = run(tmp_path, RACY, [case]).only_result()
    assert result["output"]["final"][0] < 1200


def test_a_worker_error_names_phase_worker_and_op(tmp_path):
    failing = script(*[("fail", [at]) for at in range(5)])
    result = run(tmp_path, LOCKED, [stress_case("s", [increments(1), failing])]).only_result()
    assert (result["status"], result["phase"], result["worker"], result["op_index"]) == (
        "error",
        "worker",
        1,
        3,
    )


def test_a_worker_error_reports_unfinished_workers(tmp_path):
    failing = script(("fail", [3]))
    waiting = script(("wait", []))
    run_ = run(tmp_path, LOCKED, [stress_case("s", [waiting, failing])])
    progress = run_.only_result()["progress"]
    assert {"worker": 0, "completed": 0, "in_op": True} in progress


def test_a_deadline_with_waiting_workers_is_stalled(tmp_path):
    waiting = script(("wait", []))
    run_ = run(tmp_path, LOCKED, [stress_case("s", [waiting, increments(1)])])
    result = run_.only_result()
    assert (result["status"], result["progress"]) == (
        "stalled",
        [{"worker": 0, "completed": 0, "in_op": True}],
    )


def test_leftover_threads_request_a_restart(tmp_path):
    waiting = script(("wait", []))
    run_ = run(tmp_path, LOCKED, [stress_case("s", [waiting, increments(1)])])
    assert (run_.exit_code, [event["event"] for event in run_.events[-2:]]) == (
        RESTART_EXIT_CODE,
        ["case_result", "restart_requested"],
    )


def test_probe_sections_count_violations_without_a_lock(tmp_path):
    probe = script(("@enter", ["data", "exclusive"]), ("@pause", [5]), ("@exit", ["data"]))
    worker = {"ops": probe["ops"] * 50, "args": probe["args"] * 50}
    result = run(tmp_path, LOCKED, [stress_case("s", [worker, worker, worker])]).only_result()
    section = result["sections"]["data"]
    assert (section["entries"], section["violations"] > 0) == (150, True)


def test_exit_without_enter_is_a_harness_error(tmp_path):
    worker = script(("@exit", ["data"]))
    result = run(tmp_path, LOCKED, [stress_case("s", [worker, increments(1)])]).only_result()
    assert result["error"]["type"] == "HarnessError"


def test_async_workers_run_on_one_loop(tmp_path):
    adds = script(*[("fail", [1])] * 20)
    result = run(tmp_path, ASYNC, [stress_case("s", [adds, adds])], "async").only_result()
    assert result["status"] == "ok"


def test_async_runs_with_one_seed_are_identical(tmp_path):
    adds = script(*[("fail", [1])] * 20)
    cases = [stress_case(name, [adds, adds], seed=7, yield_probability=0.3) for name in "ab"]
    first, second = run(tmp_path, ASYNC, cases, "async").named("case_result")
    assert first["output"] == second["output"]


def test_async_stalls_at_the_deadline(tmp_path):
    waiting = script(("wait", []))
    result = run(tmp_path, ASYNC, [stress_case("s", [waiting, waiting])], "async").only_result()
    assert result["status"] == "stalled"


def test_async_sequential_cases_await_results(tmp_path):
    case = {"id": "ex1", "ops": ["Counter", "fail", "get"], "args": [[], [2], []]}
    result = run(tmp_path, ASYNC, [case], "async").only_result()
    assert result["output"] == [None, 2, 2]


def test_threads_sequential_cases_run_like_design_cases(tmp_path):
    case = {"id": "ex1", "ops": ["Counter", "increment", "get"], "args": [[], [], []]}
    assert run(tmp_path, LOCKED, [case]).only_result()["output"] == [None, None, 1]


def test_setup_failures_name_the_setup_phase(tmp_path):
    case = stress_case("s", [increments(1), increments(1)])
    case["stress"]["setup"] = script(("Counter", []), ("fail", [3]))
    result = run(tmp_path, LOCKED, [case]).only_result()
    assert (result["phase"], result["op_index"]) == ("setup", 1)


@pytest.mark.parametrize("granularity", ["instruction", "none"])
def test_every_granularity_runs(tmp_path, granularity):
    case = stress_case("s", [increments(50)] * 2, python_granularity=granularity)
    assert run(tmp_path, LOCKED, [case]).only_result()["output"]["final"] == [100]


def test_an_unknown_model_is_a_bad_request(tmp_path):
    assert run(tmp_path, LOCKED, [], model="processes").exit_code == BAD_REQUEST_EXIT_CODE
