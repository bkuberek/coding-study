import json
from typing import Any

import pytest

from coding_study.adapters.runner_protocol import (
    BenchBudgetExceeded,
    BenchError,
    BenchMemory,
    BenchOutputEvent,
    BenchSampleEvent,
    BenchStart,
    LoadError,
    decode_event,
    encode_bench_request,
)
from coding_study.domain.bench_runs import (
    BenchInput,
    BenchJob,
    BenchRequest,
    BenchSample,
    BenchSettings,
    BenchTarget,
    MemoryMeasurement,
    Warmup,
)
from coding_study.domain.cases import FunctionInput, OperationSequence
from coding_study.domain.errors import RunnerProtocolError
from coding_study.domain.naming import ClassNames, FunctionNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import FileTarget, InvalidOutput, Raised, UserError
from coding_study.domain.signature import ClassSignature, FunctionSignature, Method, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType

INT = ScalarType(Scalar.INT)
ECHO = FunctionSignature("echo", (Param("value", INT),), Returns(INT))
SETTINGS = BenchSettings(7, Warmup(3, 20, 0.05), 2000, True, 1_000_000)
NAMES = FunctionNames("echo", {"value": "value"})


def bench_job(**overrides: Any) -> BenchJob:
    fields: dict[str, Any] = {
        "job_id": "echo",
        "kind": ProblemKind.FUNCTION,
        "signature": ECHO,
        "targets": (
            BenchTarget("user", FileTarget("/abs/user.py"), NAMES, emits_output=True),
            BenchTarget("brute", FileTarget("/abs/brute.py"), NAMES),
        ),
        "inputs": (BenchInput(10, FunctionInput({"value": 10}), 100),),
        "settings": SETTINGS,
        "hang_guard_ms": 10_000,
    }
    return BenchJob(**(fields | overrides))


def encoded_job(**overrides: Any) -> dict[str, Any]:
    return encode_bench_request(BenchRequest(bench_job(**overrides)))["jobs"][0]  # type: ignore[index,return-value]


def event(**fields: Any) -> str:
    return json.dumps({"job_id": "echo", "target_id": "user", "size": 10, **fields})


def test_a_bench_request_has_bench_mode():
    assert encode_bench_request(BenchRequest(bench_job()))["mode"] == "bench"


def test_a_bench_request_holds_one_job():
    assert len(encode_bench_request(BenchRequest(bench_job()))["jobs"]) == 1  # type: ignore[arg-type]


def test_targets_carry_their_id_target_and_names():
    assert encoded_job()["targets"][1] == {
        "target_id": "brute",
        "target": {"path": "/abs/brute.py"},
        "names": {"function": "echo", "params": {"value": "value"}},
    }


def test_output_targets_are_flagged():
    assert encoded_job()["targets"][0]["output"] is True


def test_function_inputs_carry_their_arguments():
    assert encoded_job()["inputs"] == [{"size": 10, "input": {"value": 10}, "max_batch": 100}]


def test_class_inputs_carry_their_operations():
    sequence = OperationSequence(("Counter", "add"), ((0,), (1,)))
    signature = ClassSignature(
        "Counter", (Param("start", INT),), (Method("add", (Param("x", INT),), Returns(INT)),)
    )
    job = encoded_job(
        kind=ProblemKind.DESIGN,
        signature=signature,
        targets=(BenchTarget("user", FileTarget("/u.py"), ClassNames("Counter", {"add": "add"})),),
        inputs=(BenchInput(1, sequence, 1),),
    )
    assert job["inputs"] == [
        {"size": 1, "ops": ["Counter", "add"], "args": [[0], [1]], "max_batch": 1}
    ]


def test_settings_are_sent():
    assert encoded_job()["settings"] == {
        "reps": 7,
        "warmup": {"min": 3, "max": 20, "cv": 0.05},
        "budget_ms": 2000,
        "memory": True,
        "min_sample_ns": 1_000_000,
    }


def test_the_hang_guard_stays_cli_side():
    assert "hang_guard_ms" not in json.dumps(encoded_job())


def test_the_signature_is_encoded_like_a_test_job():
    assert encoded_job()["signature"]["function"]["name"] == "echo"


def test_a_job_needs_ascending_sizes():
    inputs = (BenchInput(10, FunctionInput({}), 1), BenchInput(5, FunctionInput({}), 1))
    with pytest.raises(ValueError, match="ascending"):
        bench_job(inputs=inputs)


def test_a_job_needs_distinct_target_ids():
    target = BenchTarget("user", FileTarget("/u.py"), NAMES)
    with pytest.raises(ValueError, match="duplicate target"):
        bench_job(targets=(target, target))


def test_bench_start_names_the_target_and_size():
    assert decode_event(event(event="bench_start")) == BenchStart("echo", "user", 10)


def test_bench_sample_decodes_its_timings():
    line = event(event="bench_sample", rep=2, wall_ns=900, cpu_ns=800, calls=3)
    assert decode_event(line) == BenchSampleEvent("echo", "user", 10, BenchSample(2, 900, 800, 3))


def test_bench_sample_defaults_to_one_call():
    line = event(event="bench_sample", rep=1, wall_ns=900, cpu_ns=800)
    decoded = decode_event(line)
    assert isinstance(decoded, BenchSampleEvent)
    assert decoded.sample.calls == 1


def test_bench_memory_decodes_metric_and_bytes():
    line = event(event="bench_memory", metric="tracemalloc_peak", bytes=4096)
    expected = BenchMemory("echo", "user", 10, MemoryMeasurement("tracemalloc_peak", 4096))
    assert decode_event(line) == expected


def test_bench_budget_exceeded_decodes_the_call_duration():
    line = event(event="bench_budget_exceeded", wall_ns=5_000_000_000)
    assert decode_event(line) == BenchBudgetExceeded("echo", "user", 10, 5_000_000_000)


def test_bench_output_decodes_the_output():
    assert decode_event(event(event="bench_output", output=[0, 1])) == BenchOutputEvent(
        "echo", "user", 10, [0, 1]
    )


def test_bench_output_may_be_null():
    decoded = decode_event(event(event="bench_output", output=None))
    assert isinstance(decoded, BenchOutputEvent)
    assert decoded.output is None


def test_bench_error_decodes_a_raised_outcome():
    line = event(
        event="bench_error",
        status="error",
        error={"type": "ValueError", "message": "x"},
        duration_ns=5,
    )
    expected = BenchError("echo", "user", 10, Raised(UserError("ValueError", "x"), 5))
    assert decode_event(line) == expected


def test_bench_error_decodes_an_invalid_output():
    line = event(event="bench_error", status="invalid_output", reason="not an int", duration_ns=5)
    assert decode_event(line) == BenchError("echo", "user", 10, InvalidOutput("not an int", 5))


def test_bench_error_rejects_an_ok_status():
    line = event(event="bench_error", status="ok", output=1, duration_ns=5)
    with pytest.raises(RunnerProtocolError, match="bench_error"):
        decode_event(line)


def test_a_target_load_error_names_its_target():
    line = json.dumps(
        {
            "event": "load_error",
            "job_id": "echo",
            "target_id": "user",
            "error": {"type": "E", "message": "m"},
        }
    )
    assert decode_event(line) == LoadError("echo", UserError("E", "m"), "user")


def test_a_job_load_error_names_no_target():
    line = json.dumps(
        {"event": "load_error", "job_id": "echo", "error": {"type": "E", "message": "m"}}
    )
    decoded = decode_event(line)
    assert isinstance(decoded, LoadError)
    assert decoded.target_id is None
