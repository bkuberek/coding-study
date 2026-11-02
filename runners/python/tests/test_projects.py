"""Grading jobs: class jobs whose target is a project folder
(docs/specs/runners.md#grading-job)."""

import pytest

from cs_runner.program import BAD_REQUEST_EXIT_CODE, RESTART_EXIT_CODE
from tests.project_harness import (
    conformance_cases,
    conformance_project,
    project_job,
    run_project,
    write_project,
)
from tests.runner_harness import (
    COUNTER_SOURCE,
    Event,
    RunnerRun,
    class_job,
    run_jobs,
    write_source,
)

COUNTS = {"id": "counts", "ops": ["Counter", "add", "add"], "args": [[1], [2], [3]]}
SPLIT_COUNTER = {
    "counter/counter.py": """
        from counter.limits import checked
        from .limits import LIMIT


        class Counter:
            def __init__(self, start):
                self.total = min(start, LIMIT)

            def add(self, amount):
                self.total = checked(self.total + amount)
                return self.total

            def reset(self):
                self.total = 0
    """,
    "counter/limits.py": """
        LIMIT = 100


        def checked(total):
            if total > LIMIT:
                raise ValueError(f"over {LIMIT}")
            return total
    """,
}


@pytest.fixture
def split_counter(tmp_path):
    return write_project(tmp_path / "project", SPLIT_COUNTER)


def test_the_entry_imports_its_siblings_by_package_and_relative_path(split_counter):
    run = run_project(split_counter, project_job(split_counter, "counter.counter", [COUNTS]))
    assert run.only_result()["output"] == [None, 3, 6]


def test_a_grading_job_completes_like_any_class_job(split_counter):
    run = run_project(split_counter, project_job(split_counter, "counter.counter", [COUNTS]))
    assert (run.exit_code, run.events[-1]) == (0, {"event": "bye"})


def test_a_trace_names_project_files_relative_to_the_root(split_counter):
    case = {"id": "over", "ops": ["Counter", "add"], "args": [[0], [101]]}
    run = run_project(split_counter, project_job(split_counter, "counter.counter", [case]))
    assert run.only_result()["error"]["trace"] == (
        "counter/counter.py:11 in Counter.add\ncounter/limits.py:7 in checked"
    )


def test_a_package_with_an_init_file_is_an_entry(tmp_path):
    root = write_project(tmp_path / "project", {"counter/__init__.py": COUNTER_SOURCE})
    run = run_project(root, project_job(root, "counter", [COUNTS]))
    assert run.only_result()["output"] == [None, 3, 6]


def test_a_missing_entry_module_is_symbol_not_found(tmp_path):
    root = write_project(tmp_path / "project", {"counter/other.py": COUNTER_SOURCE})
    error = run_project(root, project_job(root, "counter.counter", [COUNTS])).named("load_error")
    assert error[0]["error"] == {
        "type": "SymbolNotFound",
        "message": "the project has no module counter.counter; it must define class Counter",
    }


def test_a_missing_entry_class_is_symbol_not_found(tmp_path):
    root = write_project(tmp_path / "project", {"counter/counter.py": "class Other:\n    pass\n"})
    error = run_project(root, project_job(root, "counter.counter", [COUNTS])).named("load_error")
    assert error[0]["error"] == {
        "type": "SymbolNotFound",
        "message": "counter.counter has no class Counter",
    }


def test_a_failing_import_inside_the_project_is_a_load_error_with_its_trace(tmp_path):
    root = write_project(tmp_path / "project", {"counter/counter.py": "import missing_library\n"})
    error = run_project(root, project_job(root, "counter.counter", [COUNTS])).named("load_error")
    assert error[0]["error"] == {
        "type": "ModuleNotFoundError",
        "message": "No module named 'missing_library'",
        "trace": "counter/counter.py:1 in <module>",
    }


def test_a_project_module_named_after_the_standard_library_does_not_shadow_it(tmp_path):
    files = {"counter/counter.py": COUNTER_SOURCE, "random.py": "raise ImportError('shadowed')\n"}
    root = write_project(tmp_path / "project", files)
    run = run_project(root, project_job(root, "counter.counter", [COUNTS]))
    assert run.only_result()["output"] == [None, 3, 6]


def test_project_modules_compile_from_source_on_every_run(split_counter):
    """The edit keeps the file's size and lands within the same second, which cached bytecode
    would not notice."""
    case = {"id": "over", "ops": ["Counter", "add"], "args": [[0], [150]]}
    job = project_job(split_counter, "counter.counter", [case])
    run_project(split_counter, job)
    limits = split_counter / "counter" / "limits.py"
    limits.write_text(limits.read_text().replace("100", "200"), encoding="utf-8")
    assert run_project(split_counter, job).only_result()["output"] == [None, 150]


def test_a_project_job_with_a_file_target_runs_like_a_class_job(tmp_path):
    """How `cstudy verify` loads a generated stub of a project problem."""
    path = write_source(tmp_path, COUNTER_SOURCE)
    job = class_job(path, [COUNTS]) | {"kind": "project"}
    assert run_jobs(tmp_path, job).only_result()["output"] == [None, 3, 6]


def test_a_project_target_without_its_module_is_a_bad_request(tmp_path):
    job = project_job(tmp_path, "counter", [COUNTS])
    del job["target"]["module"]
    assert run_jobs(tmp_path, job).exit_code == BAD_REQUEST_EXIT_CODE


def test_the_conformance_project_passes_its_cases(tmp_path):
    root = conformance_project("conformance-project-python", "reference", tmp_path / "project")
    signature = {
        "class": {
            "name": "Inventory",
            "constructor": {"params": []},
            "methods": [
                {
                    "name": "add",
                    "params": [
                        {"name": "name", "type": "string"},
                        {"name": "count", "type": "int"},
                    ],
                    "returns": {"type": "int"},
                },
                {
                    "name": "label",
                    "params": [{"name": "name", "type": "string"}],
                    "returns": {"type": "string"},
                },
            ],
        }
    }
    cases = conformance_cases("conformance-project-python")
    run = run_project(root, project_job(root, "store.inventory", cases, signature))
    assert [result["output"] for result in run.named("case_result")] == [
        [None, 3, 5, "pens: 5"],
        [None, "ink: 0"],
    ]


# The virtual clock (docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs)

CLOCK_FIXTURE = "conformance-project-clock-python"


def _method(name: str, params: dict[str, str], returns: str) -> Event:
    declared = [{"name": param, "type": kind} for param, kind in params.items()]
    return {"name": name, "params": declared, "returns": {"type": returns}}


INBOX_SIGNATURE: Event = {
    "class": {
        "name": "Inbox",
        "constructor": {"params": []},
        "methods": [
            _method("publish", {"body": "string"}, "int"),
            _method("receive", {"waitMs": "int"}, "string") | {"async": True},
            _method("sleep", {"ms": "int"}, "long") | {"async": True},
            _method("race", {"names": "string"}, "string") | {"async": True},
            _method("hold", {}, "string") | {"async": True},
            _method("jam", {}, "string"),
            _method("leave", {}, "void"),
            _method("strand", {}, "void"),
        ],
    }
}
CLOCKED_COUNTER = {
    "counter/counter.py": """
        import asyncio


        class Counter:
            def __init__(self, start):
                self.total = start

            async def add(self, amount):
                await asyncio.sleep(abs(amount) / 1000)
                if amount < 0:
                    raise ValueError("negative amount")
                self.total += amount
                return self.total

            def reset(self):
                print("reset")
                self.total = 0
    """,
}


def on_the_clock(job: Event, seed: int | None = None) -> Event:
    clock: Event = {"clock": "virtual"}
    return job | clock | ({} if seed is None else {"clock_seed": seed})


@pytest.fixture
def inbox(tmp_path):
    return conformance_project(CLOCK_FIXTURE, "reference", tmp_path / "project")


def clock_cases(*case_ids: str) -> list[Event]:
    cases = {case["id"]: case for case in conformance_cases(CLOCK_FIXTURE)}
    return [cases[case_id] for case_id in case_ids]


def grade_inbox(root, *case_ids: str, seed: int | None = None) -> RunnerRun:
    job = project_job(root, "inbox.inbox", clock_cases(*case_ids), INBOX_SIGNATURE)
    return run_project(root, on_the_clock(job, seed))


@pytest.fixture
def counter(tmp_path):
    return write_project(tmp_path / "project", CLOCKED_COUNTER)


def grade_counter(root, *cases: Event) -> RunnerRun:
    return run_project(root, on_the_clock(project_job(root, "counter.counter", list(cases))))


def test_the_runner_announces_the_clock(inbox):
    (hello,) = grade_inbox(inbox, "ex1").named("hello")
    assert "clock" in hello["features"]


def test_each_case_runs_on_a_virtual_clock_of_its_own(inbox):
    run = grade_inbox(inbox, "ex1", "advance", "spawn-join", "after-deadlock", "last")
    assert [result["output"] for result in run.named("case_result")] == [
        [None, 1, 2, "a"],
        [None, 0, None, 1500, 2500, 4000],
        [None, None, None, 1, "a", 1000, "", 3000],
        [None, None, 10],
        [None, 1],
    ]


def test_ties_fire_in_the_order_of_seed_zero_by_default(inbox):
    assert grade_inbox(inbox, "ties").only_result()["output"] == [None, "bacd", 10]


def test_the_job_names_the_seed_that_orders_ties(inbox):
    outputs = {grade_inbox(inbox, "ties", seed=seed).only_result()["output"][1] for seed in (1, 2)}
    assert outputs == {"dabc", "cbda"}


def test_a_join_that_waits_for_good_is_stalled_at_once(inbox):
    run = grade_inbox(inbox, "deadlock", "after-deadlock")
    stalled, after = run.named("case_result")
    assert {key: stalled[key] for key in ("status", "op_index", "reason", "partial_output")} == {
        "status": "stalled",
        "op_index": 3,
        "reason": "op 3 (@join r1): deadlock at 2000 ms",
        "partial_output": [None, None, None],
    }
    assert (after["output"], run.named("restart_requested"), run.exit_code) == (
        [None, None, 10],
        [],
        0,
    )


def test_an_awaited_call_that_waits_for_good_is_stalled_at_its_operation(inbox):
    case = {"id": "holds", "ops": ["Inbox", "@advance", "hold"], "args": [[], [5], []]}
    job = project_job(inbox, "inbox.inbox", [case], INBOX_SIGNATURE)
    result = run_project(inbox, on_the_clock(job)).only_result()
    assert (result["status"], result["reason"]) == ("stalled", "op 2 (hold): deadlock at 5 ms")


def test_a_task_left_waiting_is_cancelled_when_the_case_ends(inbox):
    run = grade_inbox(inbox, "leftover", "last")
    assert [result["output"] for result in run.named("case_result")] == [[None, None, 0], [None, 1]]


def test_a_thread_left_running_makes_the_runner_ask_for_a_restart(inbox):
    run = grade_inbox(inbox, "strand", "last")
    assert run.only_result()["output"] == [None, None, 0]
    assert (run.named("restart_requested")[0]["reason"], run.exit_code) == (
        "1 threads of strand are still running",
        RESTART_EXIT_CODE,
    )


def test_an_async_result_is_awaited_while_the_clock_moves(counter):
    case = {"id": "adds", "ops": ["Counter", "add", "add", "@now"], "args": [[0], [5], [10], []]}
    assert grade_counter(counter, case).only_result()["output"] == [None, 5, 15, 15]


def test_a_spawned_call_that_raises_fails_its_join(counter):
    case = {
        "id": "fails",
        "ops": ["Counter", "@spawn", "@join"],
        "args": [[0], ["t", "add", -1], ["t"]],
    }
    result = grade_counter(counter, case).only_result()
    assert {key: result[key] for key in ("status", "op_index", "partial_output")} == {
        "status": "error",
        "op_index": 2,
        "partial_output": [None, None],
    }
    assert result["error"]["message"] == "negative amount"


def test_a_join_of_a_task_never_spawned_is_an_input_error(counter):
    case = {"id": "joins", "ops": ["Counter", "@join"], "args": [[0], ["t"]]}
    result = grade_counter(counter, case).only_result()
    assert (result["status"], result["op_index"], result["error"]["type"]) == (
        "error",
        1,
        "CaseInputError",
    )


def test_what_a_case_prints_is_its_output(counter):
    case = {"id": "prints", "ops": ["Counter", "reset"], "args": [[0], []]}
    result = grade_counter(counter, case).only_result()
    assert (result["output"], result["stdout"]) == ([None, None], "reset\n")


def test_an_unknown_clock_is_a_bad_request(counter):
    job = project_job(counter, "counter.counter", [COUNTS]) | {"clock": "real"}
    assert run_project(counter, job).exit_code == BAD_REQUEST_EXIT_CODE


def test_only_a_project_job_runs_on_the_clock(tmp_path):
    path = write_source(tmp_path, COUNTER_SOURCE)
    assert run_jobs(tmp_path, on_the_clock(class_job(path, [COUNTS]))).exit_code == (
        BAD_REQUEST_EXIT_CODE
    )
