import json
import os
import platform

import pytest

from cs_runner.program import BAD_REQUEST_EXIT_CODE
from tests.runner_harness import (
    COUNTER_SOURCE,
    class_job,
    function_job,
    request_of,
    run_jobs,
    run_request_text,
    write_source,
)

ECHO_SOURCE = """
def echo(value):
    return value
"""
FAILING_SOURCE = """
def echo(value):
    return helper(value)


def helper(value):
    raise IndexError("list index out of range")
"""


def echo_case(case_id: str = "c1", value: object = 1) -> dict[str, object]:
    return {"id": case_id, "input": {"value": value}}


def ops_case(ops: list[str], args: list[list[object]]) -> dict[str, object]:
    return {"id": "ops", "ops": ops, "args": args}


@pytest.fixture
def echo_file(tmp_path):
    return write_source(tmp_path, ECHO_SOURCE)


@pytest.fixture
def counter_file(tmp_path):
    return write_source(tmp_path, COUNTER_SOURCE)


def test_an_empty_request_says_hello_then_bye(tmp_path):
    run = run_jobs(tmp_path)
    assert [event["event"] for event in run.events] == ["hello", "bye"]


def test_hello_names_the_runner_protocol_and_runtime(tmp_path):
    hello = run_jobs(tmp_path).events[0]
    assert hello == {
        "event": "hello",
        "runner": "python",
        "protocol": 1,
        "runtime": platform.python_version(),
        "features": ["stress"],
    }


def test_a_completed_run_exits_zero(tmp_path, echo_file):
    assert run_jobs(tmp_path, function_job(echo_file, [echo_case()])).exit_code == 0


def test_events_frame_each_case_inside_its_job(tmp_path, echo_file):
    run = run_jobs(tmp_path, function_job(echo_file, [echo_case("a"), echo_case("b")]))
    names = [(event["event"], event.get("case_id")) for event in run.events[1:-1]]
    assert names == [
        ("job_start", None),
        ("case_start", "a"),
        ("case_result", "a"),
        ("case_start", "b"),
        ("case_result", "b"),
        ("job_end", None),
    ]


def test_a_returned_value_is_ok_with_its_output(tmp_path, echo_file):
    result = run_jobs(tmp_path, function_job(echo_file, [echo_case(value=42)])).only_result()
    assert (result["status"], result["output"]) == ("ok", 42)


def test_a_result_carries_a_duration(tmp_path, echo_file):
    result = run_jobs(tmp_path, function_job(echo_file, [echo_case()])).only_result()
    assert result["duration_ns"] >= 0


def test_empty_stdout_is_omitted(tmp_path, echo_file):
    result = run_jobs(tmp_path, function_job(echo_file, [echo_case()])).only_result()
    assert "stdout" not in result


def test_an_exception_is_an_error_with_a_user_trace(tmp_path):
    path = write_source(tmp_path, FAILING_SOURCE)
    result = run_jobs(tmp_path, function_job(path, [echo_case()])).only_result()
    assert result["error"] == {
        "type": "IndexError",
        "message": "list index out of range",
        "trace": "solution.py:3 in echo\nsolution.py:7 in helper",
    }


def test_system_exit_is_a_case_error(tmp_path):
    path = write_source(tmp_path, "import sys\n\ndef echo(value):\n    sys.exit(3)\n")
    result = run_jobs(tmp_path, function_job(path, [echo_case()])).only_result()
    assert (result["status"], result["error"]["type"]) == ("error", "SystemExit")


def test_output_is_captured_per_case(tmp_path):
    path = write_source(tmp_path, "def echo(value):\n    print('saw', value)\n    return value\n")
    run = run_jobs(tmp_path, function_job(path, [echo_case("a", 1), echo_case("b", 2)]))
    assert [result["stdout"] for result in run.named("case_result")] == ["saw 1\n", "saw 2\n"]


def test_a_return_value_of_the_wrong_type_is_invalid_output(tmp_path):
    path = write_source(tmp_path, "def echo(value):\n    return str(value)\n")
    result = run_jobs(tmp_path, function_job(path, [echo_case()])).only_result()
    assert (result["status"], result["reason"]) == ("invalid_output", "expected int, got str")


def test_a_bad_case_input_is_reported_as_an_error(tmp_path, echo_file):
    result = run_jobs(tmp_path, function_job(echo_file, [echo_case(value="x")])).only_result()
    assert result["error"]["type"] == "CaseInputError"


def test_load_error_replaces_the_case_events(tmp_path):
    job = function_job(tmp_path / "missing.py", [echo_case()])
    names = [event["event"] for event in run_jobs(tmp_path, job).events]
    assert names == ["hello", "job_start", "load_error", "job_end", "bye"]


def test_a_missing_file_is_a_load_error(tmp_path):
    run = run_jobs(tmp_path, function_job(tmp_path / "missing.py", [echo_case()]))
    assert run.named("load_error")[0]["error"]["type"] == "FileNotFoundError"


@pytest.mark.parametrize(
    ("source", "error_type"),
    [
        ("def echo_typo(value):\n    return value\n", "AttributeError"),
        ("echo = 5\n", "TypeError"),
        ("def echo():\n    return 1\n", "TypeError"),
        ("def echo(value)\n    return value\n", "SyntaxError"),
        ("raise RuntimeError('import failed')\n", "RuntimeError"),
    ],
    ids=["missing-symbol", "not-callable", "arity", "syntax", "import-time-exception"],
)
def test_an_unusable_target_is_a_load_error(tmp_path, source, error_type):
    path = write_source(tmp_path, source)
    run = run_jobs(tmp_path, function_job(path, [echo_case()]))
    assert run.named("load_error")[0]["error"]["type"] == error_type


def test_the_user_file_is_compiled_from_its_current_source(tmp_path):
    path = write_source(tmp_path, "def echo(value):\n    return 1\n")
    run_jobs(tmp_path, function_job(path, [echo_case()]))
    stat = path.stat()
    write_source(tmp_path, "def echo(value):\n    return 2\n")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    result = run_jobs(tmp_path, function_job(path, [echo_case()])).only_result()
    assert result["output"] == 2


def test_deep_recursion_does_not_overflow(tmp_path):
    source = "def echo(value):\n    return 0 if value == 0 else 1 + echo(value - 1)\n"
    path = write_source(tmp_path, source)
    result = run_jobs(tmp_path, function_job(path, [echo_case(value=50_000)])).only_result()
    assert result["output"] == 50_000


def test_operations_return_one_output_each(tmp_path, counter_file):
    case = ops_case(["Counter", "add", "reset", "add"], [[10], [5], [], [1]])
    result = run_jobs(tmp_path, class_job(counter_file, [case])).only_result()
    assert result["output"] == [None, 15, None, 1]


def test_an_operation_error_names_the_operation_and_earlier_outputs(tmp_path, counter_file):
    case = ops_case(["Counter", "add", "add", "add"], [[0], [1], [-1], [1]])
    result = run_jobs(tmp_path, class_job(counter_file, [case])).only_result()
    failure = {key: result[key] for key in ("status", "op_index", "partial_output")}
    assert failure == {"status": "error", "op_index": 2, "partial_output": [None, 1]}


def test_a_constructor_error_is_operation_zero(tmp_path):
    path = write_source(tmp_path, COUNTER_SOURCE.replace("self.total = start", "raise KeyError"))
    case = ops_case(["Counter", "add"], [[0], [1]])
    result = run_jobs(tmp_path, class_job(path, [case])).only_result()
    assert (result["op_index"], result["partial_output"]) == (0, [])


def test_an_unknown_operation_is_a_case_input_error(tmp_path, counter_file):
    case = ops_case(["Counter", "multiply"], [[0], [2]])
    result = run_jobs(tmp_path, class_job(counter_file, [case])).only_result()
    assert result["error"]["type"] == "CaseInputError"


def test_a_missing_method_is_a_load_error(tmp_path):
    path = write_source(tmp_path, COUNTER_SOURCE.replace("def reset", "def clear"))
    run = run_jobs(tmp_path, class_job(path, [ops_case(["Counter"], [[0]])]))
    assert "reset" in run.named("load_error")[0]["error"]["message"]


def test_a_class_name_that_is_not_a_class_is_a_load_error(tmp_path):
    path = write_source(tmp_path, "def Counter(start):\n    return start\n")
    run = run_jobs(tmp_path, class_job(path, [ops_case(["Counter"], [[0]])]))
    assert run.named("load_error")[0]["error"]["type"] == "TypeError"


@pytest.mark.parametrize(
    "request_text",
    [
        "not json",
        json.dumps({**request_of(), "protocol": 2}),
        json.dumps({**request_of(), "mode": "stress"}),
        json.dumps({"protocol": 1, "mode": "test", "jobs": [{"job_id": "x"}]}),
        json.dumps({"protocol": 1, "mode": "bench", "jobs": [{"job_id": "x"}]}),
    ],
    ids=["invalid-json", "unknown-protocol", "unknown-mode", "malformed-job", "malformed-bench"],
)
def test_a_bad_request_exits_with_code_two(tmp_path, request_text):
    assert run_request_text(tmp_path, request_text).exit_code == BAD_REQUEST_EXIT_CODE


def test_a_bad_request_still_says_hello_first(tmp_path):
    run = run_request_text(tmp_path, "not json")
    assert [event["event"] for event in run.events] == ["hello"]
