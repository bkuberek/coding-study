"""Runs `cs_runner` in process on a request built from plain dictionaries."""

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cs_runner.program import main

type Event = dict[str, Any]

ECHO_SIGNATURE: dict[str, Any] = {
    "function": {
        "name": "echo",
        "params": [{"name": "value", "type": "int"}],
        "returns": {"type": "int"},
    }
}
COUNTER_SIGNATURE: dict[str, Any] = {
    "class": {
        "name": "Counter",
        "constructor": {"params": [{"name": "start", "type": "int"}]},
        "methods": [
            {
                "name": "add",
                "params": [{"name": "amount", "type": "int"}],
                "returns": {"type": "int"},
            },
            {"name": "reset", "params": [], "returns": {"type": "void"}},
        ],
    }
}
COUNTER_SOURCE = """
class Counter:
    def __init__(self, start):
        self.total = start

    def add(self, amount):
        if amount < 0:
            raise ValueError("negative amount")
        self.total += amount
        return self.total

    def reset(self):
        self.total = 0
"""


@dataclass(frozen=True, slots=True)
class RunnerRun:
    exit_code: int
    events: list[Event]

    def named(self, event: str) -> list[Event]:
        return [line for line in self.events if line["event"] == event]

    def only_result(self) -> Event:
        (result,) = self.named("case_result")
        return result


def write_source(directory: Path, source: str, name: str = "solution.py") -> Path:
    path = directory / name
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


def function_job(path: Path, cases: list[Event], signature: Event = ECHO_SIGNATURE) -> Event:
    function = signature["function"]
    params = {param["name"]: param["name"] for param in function["params"]}
    return {
        "job_id": "job",
        "kind": "function",
        "target": {"path": str(path)},
        "names": {"function": function["name"], "params": params},
        "signature": signature,
        "cases": cases,
    }


def class_job(path: Path, cases: list[Event], signature: Event = COUNTER_SIGNATURE) -> Event:
    declared = signature["class"]
    methods = {method["name"]: method["name"] for method in declared["methods"]}
    return {
        "job_id": "job",
        "kind": "design",
        "target": {"path": str(path)},
        "names": {"class": declared["name"], "methods": methods},
        "signature": signature,
        "cases": cases,
    }


def request_of(*jobs: Event) -> Event:
    return {"protocol": 1, "mode": "test", "jobs": list(jobs)}


BENCH_SETTINGS: dict[str, Any] = {
    "reps": 3,
    "warmup": {"min": 1, "max": 1, "cv": 0.05},
    "budget_ms": 2000,
    "memory": False,
    "min_sample_ns": 0,
}


def bench_target(path: Path, target_id: str, signature: Event = ECHO_SIGNATURE) -> Event:
    """A target of a bench job, named like `function_job` or `class_job` names it."""
    builder = class_job if "class" in signature else function_job
    job = builder(path, [], signature)
    return {"target_id": target_id, "target": job["target"], "names": job["names"]}


def bench_job(
    targets: list[Event],
    inputs: list[Event],
    signature: Event = ECHO_SIGNATURE,
    **settings: Any,
) -> Event:
    return {
        "job_id": "job",
        "kind": "design" if "class" in signature else "function",
        "signature": signature,
        "targets": targets,
        "inputs": inputs,
        "settings": BENCH_SETTINGS | settings,
    }


def bench_request_of(*jobs: Event) -> Event:
    return {"protocol": 1, "mode": "bench", "jobs": list(jobs)}


def run_bench_jobs(directory: Path, *jobs: Event) -> RunnerRun:
    return run_request_text(directory, json.dumps(bench_request_of(*jobs)))


def run_request_text(directory: Path, request_text: str) -> RunnerRun:
    request_path = directory / "request.json"
    events_path = directory / "events.jsonl"
    request_path.write_text(request_text, encoding="utf-8")
    exit_code = main(["--request", str(request_path), "--out", str(events_path)])
    lines = events_path.read_text(encoding="utf-8").splitlines()
    return RunnerRun(exit_code, [json.loads(line) for line in lines])


def run_jobs(directory: Path, *jobs: Event) -> RunnerRun:
    return run_request_text(directory, json.dumps(request_of(*jobs)))
