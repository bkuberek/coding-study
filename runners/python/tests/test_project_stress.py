"""Stress cases in a project's grading job (docs/specs/runners.md#stress-in-project-jobs): the
job runs its sequential cases, on the virtual clock when it has one, then its stress runs with the
concurrent job's code on the project's entry class."""

import pytest

from cs_runner.program import BAD_REQUEST_EXIT_CODE
from tests.project_harness import project_job, run_project, write_project
from tests.runner_harness import Event

PERTURB = {"yield_probability": 0.05, "max_yields": 3, "python_granularity": "line"}
LOCKED_COUNTER = {
    "counter/counter.py": """
        from counter.total import Total


        class Counter:
            def __init__(self, start):
                self._total = Total(start)

            def add(self, amount):
                return self._total.add(amount)

            def reset(self):
                self._total.reset()
    """,
    "counter/total.py": """
        import threading


        class Total:
            def __init__(self, start):
                self._lock = threading.Lock()
                self._value = start

            def add(self, amount):
                with self._lock:
                    value = self._value + amount
                    self._value = value
                    return value

            def reset(self):
                with self._lock:
                    self._value = 0
    """,
}
CLOCKED_COUNTER = {
    "counter/counter.py": """
        import asyncio


        class Counter:
            def __init__(self, start):
                self.total = start

            async def add(self, amount):
                await asyncio.sleep(0)
                self.total += amount
                return self.total

            def reset(self):
                self.total = 0
    """,
}
COUNTS = {"id": "counts", "ops": ["Counter", "add", "add"], "args": [[1], [2], [3]]}


def stress_run(case_id: str, workers: int = 2, repeat: int = 3) -> Event:
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


def stressed(job: Event, model: str = "threads") -> Event:
    return job | {"model": model}


@pytest.fixture
def locked(tmp_path):
    return write_project(tmp_path / "project", LOCKED_COUNTER)


def test_the_runner_announces_project_stress(locked):
    run = run_project(locked, project_job(locked, "counter.counter", [COUNTS]))
    (hello,) = run.named("hello")
    assert "project-stress" in hello["features"]


def test_a_project_job_runs_its_stress_runs_after_its_cases(locked):
    cases = [COUNTS, stress_run("s1:thread:0"), stress_run("s1:thread:1")]
    run = run_project(locked, stressed(project_job(locked, "counter.counter", cases)))
    sequential, *stress = run.named("case_result")
    assert (run.exit_code, sequential["output"]) == (0, [None, 3, 6])
    assert [result["status"] for result in stress] == ["ok", "ok"]
    assert [result["output"]["final"] for result in stress] == [[6], [6]]


def test_a_stress_run_reports_every_output_of_the_entry_class(locked):
    run = run_project(locked, stressed(project_job(locked, "counter.counter", [stress_run("s1")])))
    output = run.only_result()["output"]
    outputs = sorted(value for worker in output["workers"] for value in worker)
    assert (output["setup"], outputs) == ([None], [1, 2, 3, 4, 5, 6])


def test_a_stress_failure_names_a_file_under_the_root(tmp_path):
    raising = {
        "counter/counter.py": LOCKED_COUNTER["counter/counter.py"],
        "counter/total.py": LOCKED_COUNTER["counter/total.py"].replace(
            "value = self._value + amount", "raise KeyError(amount)"
        ),
    }
    root = write_project(tmp_path / "project", raising)
    run = run_project(root, stressed(project_job(root, "counter.counter", [stress_run("s1")])))
    result = run.only_result()
    assert (result["status"], result["phase"]) == ("error", "worker")
    assert "counter/total.py" in result["error"]["trace"]


def test_a_stress_case_without_the_model_is_a_bad_request(locked):
    run = run_project(locked, project_job(locked, "counter.counter", [stress_run("s1")]))
    assert run.exit_code == BAD_REQUEST_EXIT_CODE


def test_sequential_cases_run_on_the_clock_and_stress_runs_on_the_real_one(tmp_path):
    root = write_project(tmp_path / "project", CLOCKED_COUNTER)
    advance = {"id": "advance", "ops": ["Counter", "@advance", "@now"], "args": [[0], [5000], []]}
    job = project_job(root, "counter.counter", [advance, stress_run("s1")])
    run = run_project(root, stressed(job | {"clock": "virtual"}, "async"))
    sequential, stress = run.named("case_result")
    assert (sequential["output"], stress["status"]) == ([None, None, 5000], "ok")
    assert stress["output"]["final"] == [6]
