"""Stress cases in a project's grading job in runners/typescript/runner.ts, run as `node
runner.ts` (docs/specs/runners.md#stress-in-project-jobs): the sequential cases, on the virtual
clock when the job has one, then the stress runs in the async model. Conformance fixture 9038
covers a broken overlay; these cover the job itself."""

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
export class Counter {
  #total: number;

  constructor(start: number) {
    this.#total = start;
  }

  async add(amount: number): Promise<number> {
    this.#total += amount;
    const total = this.#total;
    await Promise.resolve();
    return total;
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
            }
        ],
    }
}
PERTURB = {"yield_probability": 0.05, "max_yields": 3, "python_granularity": "line"}


def job(root: Path, *cases: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {
        "job_id": "counter",
        "kind": "project",
        "target": {"path": str(root / "src" / "counter.ts")},
        "names": {"class": "Counter", "methods": {"add": "add"}},
        "signature": SIGNATURE,
        "cases": list(cases),
        "model": "async",
    } | fields


def stress_run(case_id: str, workers: int = 2, repeat: int = 3) -> dict[str, Any]:
    script = {"ops": ["add"] * repeat, "args": [[1]] * repeat}
    return {
        "id": case_id,
        "stress": {
            "seed": 1000,
            "deadline_ms": 5000,
            "perturb": PERTURB,
            "setup": {"ops": ["Counter"], "args": [[0]]},
            "workers": [script] * workers,
            "final": {"ops": ["add"], "args": [[0]]},
        },
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


def test_the_runner_announces_project_stress(root):
    _, events = run(root, job(root))
    assert "project-stress" in events[0]["features"]


def test_a_project_job_runs_its_stress_runs_after_its_cases(root):
    adds = {"id": "adds", "ops": ["Counter", "add", "add"], "args": [[1], [2], [3]]}
    code, events = run(root, job(root, adds, stress_run("s1:async:0")))
    sequential, stress = results(events)
    assert (code, sequential["output"], stress["status"]) == (0, [None, 3, 6], "ok")
    assert stress["output"]["final"] == [6]


def test_sequential_cases_run_on_the_clock_and_stress_runs_on_the_real_one(root):
    advance = {"id": "advance", "ops": ["Counter", "@advance", "@now"], "args": [[0], [5000], []]}
    code, events = run(root, job(root, advance, stress_run("s1:async:0"), clock="virtual"))
    sequential, stress = results(events)
    assert (code, sequential["output"], stress["status"]) == (0, [None, None, 5000], "ok")


def test_a_project_job_with_stress_runs_the_async_model_only(root):
    assert run(root, job(root, stress_run("s1"), model="threads"))[0] == BAD_REQUEST_EXIT_CODE
