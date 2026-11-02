"""Grading jobs on the virtual clock in runners/typescript/runner.ts, run as `node runner.ts`
(docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs). Conformance fixture 9036 covers
the harness operations, a chain of sleeps, ties, a deadlock and a busy loop; these cover the rest.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import REPOSITORY_ROOT

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

RUNNER_SCRIPT = REPOSITORY_ROOT / "runners" / "typescript" / "runner.ts"
TIMEOUT_SECONDS = 60
BAD_REQUEST_EXIT_CODE = 2
COUNTER = """\
import { setTimeout as sleep } from "node:timers/promises";

export class Counter {
  #total: number;

  constructor(start: number) {
    this.#total = start;
  }

  async add(amount: number): Promise<number> {
    await sleep(Math.abs(amount));
    if (amount < 0) {
      throw new Error("negative amount");
    }
    this.#total += amount;
    return this.#total;
  }

  wait(): Promise<number> {
    return new Promise(() => {});
  }
}
"""
SIGNATURE: dict[str, Any] = {
    "class": {
        "name": "Counter",
        "constructor": {"params": [{"name": "start", "type": "int"}]},
        "methods": [
            {
                "name": "add",
                "params": [{"name": "amount", "type": "int"}],
                "returns": {"type": "int"},
                "async": True,
            },
            {"name": "wait", "params": [], "returns": {"type": "int"}, "async": True},
        ],
    }
}


def job(root: Path, *cases: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {
        "job_id": "counter",
        "kind": "project",
        "target": {"path": str(root / "src" / "counter.ts")},
        "names": {"class": "Counter", "methods": {"add": "add", "wait": "wait"}},
        "signature": SIGNATURE,
        "cases": list(cases),
        "clock": "virtual",
    } | fields


def case(case_id: str, *ops: tuple[str, list[Any]]) -> dict[str, Any]:
    return {
        "id": case_id,
        "ops": ["Counter", *(op for op, _ in ops)],
        "args": [[0], *(args for _, args in ops)],
    }


@pytest.fixture
def root(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "package.json").write_text('{"type": "module"}\n')
    (project / "src" / "counter.ts").write_text(textwrap.dedent(COUNTER))
    return project


def run(root: Path, *jobs: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    request = root.parent / "request.json"
    events = root.parent / "events.jsonl"
    request.write_text(json.dumps({"protocol": 1, "mode": "test", "jobs": list(jobs)}))
    process = subprocess.run(
        ["node", str(RUNNER_SCRIPT), "--request", str(request), "--out", str(events)],
        cwd=root,
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    lines = events.read_text().splitlines() if events.exists() else []
    return process.returncode, [json.loads(line) for line in lines]


def results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["event"] == "case_result"]


def test_the_runner_announces_the_clock(root):
    _, events = run(root, job(root))
    assert "clock" in events[0]["features"]


def test_an_awaited_result_moves_the_clock_to_each_due_timer(root):
    adds = case("adds", ("add", [5]), ("add", [10]), ("@now", []))
    _, events = run(root, job(root, adds))
    assert results(events)[0]["output"] == [None, 5, 15, 15]


def test_a_spawned_call_that_rejects_fails_its_join(root):
    fails = case("fails", ("@spawn", ["t", "add", -1]), ("@join", ["t"]))
    _, events = run(root, job(root, fails))
    [result] = results(events)
    assert (result["status"], result["op_index"], result["partial_output"]) == (
        "error",
        2,
        [None, None],
    )
    assert result["error"]["message"] == "negative amount"


def test_an_awaited_call_that_waits_for_good_is_stalled_at_its_operation(root):
    waits = case("waits", ("@advance", [5]), ("wait", []))
    _, events = run(root, job(root, waits, case("after", ("add", [1]))))
    stalled, after = results(events)
    assert (stalled["status"], stalled["reason"], stalled["partial_output"]) == (
        "stalled",
        "op 2 (wait): deadlock at 5 ms",
        [None, None],
    )
    assert after["output"] == [None, 1]


def test_a_join_of_a_task_never_spawned_is_an_input_error(root):
    _, events = run(root, job(root, case("joins", ("@join", ["t"]))))
    [result] = results(events)
    assert (result["status"], result["op_index"], result["error"]["type"]) == (
        "error",
        1,
        "InvalidInput",
    )


def test_an_unknown_clock_is_a_bad_request(root):
    assert run(root, job(root, clock="real"))[0] == BAD_REQUEST_EXIT_CODE


def test_only_a_project_job_runs_on_the_clock(root):
    assert run(root, job(root, kind="design"))[0] == BAD_REQUEST_EXIT_CODE
