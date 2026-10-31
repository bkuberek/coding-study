"""Grading jobs: class jobs whose target is a project folder
(docs/specs/runners.md#grading-job)."""

import pytest

from cs_runner.program import BAD_REQUEST_EXIT_CODE
from tests.project_harness import (
    conformance_cases,
    conformance_project,
    project_job,
    run_project,
    write_project,
)
from tests.runner_harness import COUNTER_SOURCE, class_job, run_jobs, write_source

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
