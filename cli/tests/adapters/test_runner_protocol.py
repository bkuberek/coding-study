import json
from dataclasses import replace
from typing import Any, cast

import pytest

from coding_study.adapters.runner_protocol import (
    Bye,
    CaseResult,
    CaseStart,
    Hello,
    JobEnd,
    JobStart,
    LoadError,
    decode_event,
    encode_request,
)
from coding_study.domain.cases import FunctionInput, OperationSequence
from coding_study.domain.errors import RunnerProtocolError
from coding_study.domain.naming import ClassNames, FunctionNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import (
    ClassTarget,
    CompiledTarget,
    FileTarget,
    InvalidOutput,
    ProjectTarget,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunRequest,
    UserError,
)
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import (
    ArrayType,
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    VoidType,
)

INT = ScalarType(Scalar.INT)
INT_ARRAY = ArrayType(INT)
TREE = NodeType(NodeKind.TREE_NODE)

TWO_SUM_JOB = RunJob(
    job_id="two-sum",
    kind=ProblemKind.FUNCTION,
    target=FileTarget("/abs/python/practice/two_sum.py"),
    names=FunctionNames("two_sum", {"nums": "nums", "target": "target"}),
    signature=FunctionSignature(
        "twoSum", (Param("nums", INT_ARRAY), Param("target", INT)), Returns(INT_ARRAY)
    ),
    cases=(RunCase("ex1", FunctionInput({"nums": [4, 9, 2, 7], "target": 11}), 10_000),),
)
LRU_JOB = RunJob(
    job_id="lru-cache",
    kind=ProblemKind.PROGRESSIVE,
    target=ClassTarget("practice.lru_cache.LRUCache"),
    names=ClassNames("LRUCache", {"get": "get", "put": "put"}),
    signature=ClassSignature(
        "LRUCache",
        (Param("capacity", INT),),
        (
            Method("get", (Param("key", INT),), Returns(INT), level=1),
            Method("put", (Param("key", INT), Param("value", INT)), Returns(VoidType())),
        ),
    ),
    cases=(RunCase("ex1", OperationSequence(("LRUCache", "get"), ((2,), (1,))), 500),),
)


def encoded_job(job: RunJob) -> Any:
    [encoded] = cast("list[Any]", encode_request(RunRequest((job,)))["jobs"])
    return encoded


def event_line(**fields: object) -> str:
    return json.dumps(fields)


def test_encodes_the_spec_example_request():
    assert encode_request(RunRequest((TWO_SUM_JOB,))) == {
        "protocol": 1,
        "mode": "test",
        "jobs": [
            {
                "job_id": "two-sum",
                "kind": "function",
                "target": {"path": "/abs/python/practice/two_sum.py"},
                "names": {"function": "two_sum", "params": {"nums": "nums", "target": "target"}},
                "signature": {
                    "function": {
                        "name": "twoSum",
                        "params": [
                            {"name": "nums", "type": "int[]"},
                            {"name": "target", "type": "int"},
                        ],
                        "returns": {"type": "int[]"},
                    }
                },
                "cases": [{"id": "ex1", "input": {"nums": [4, 9, 2, 7], "target": 11}}],
            }
        ],
    }


def test_encodes_class_target_names_and_operation_cases():
    encoded = encoded_job(LRU_JOB)
    assert (encoded["kind"], encoded["target"], encoded["names"], encoded["cases"]) == (
        "progressive",
        {"class": "practice.lru_cache.LRUCache"},
        {"class": "LRUCache", "methods": {"get": "get", "put": "put"}},
        [{"id": "ex1", "ops": ["LRUCache", "get"], "args": [[2], [1]]}],
    )


def test_encodes_a_compiled_target_by_its_id():
    job = replace(TWO_SUM_JOB, target=CompiledTarget("ref/hash-map"))
    assert encoded_job(job)["target"] == {"compiled": "ref/hash-map"}


def test_encodes_a_project_target_by_its_root_and_entry_module():
    job = replace(
        LRU_JOB, kind=ProblemKind.PROJECT, target=ProjectTarget("/ws/projects/bank", "bank.bank")
    )
    encoded = encoded_job(job)
    assert (encoded["kind"], encoded["target"]) == (
        "project",
        {"project": "/ws/projects/bank", "module": "bank.bank"},
    )


def test_encodes_the_constructor_name_when_the_language_names_one():
    names = ClassNames("LRUCache", {"get": "Get", "put": "Put"}, constructor="NewLRUCache")
    assert encoded_job(replace(LRU_JOB, names=names))["names"] == {
        "class": "LRUCache",
        "methods": {"get": "Get", "put": "Put"},
        "constructor": "NewLRUCache",
    }


def test_encodes_class_signature_with_levels():
    assert encoded_job(LRU_JOB)["signature"] == {
        "class": {
            "name": "LRUCache",
            "constructor": {"params": [{"name": "capacity", "type": "int"}]},
            "methods": [
                {
                    "name": "get",
                    "params": [{"name": "key", "type": "int"}],
                    "returns": {"type": "int"},
                    "level": 1,
                },
                {
                    "name": "put",
                    "params": [{"name": "key", "type": "int"}, {"name": "value", "type": "int"}],
                    "returns": {"type": "void"},
                },
            ],
        }
    }


def test_encodes_modifiers_with_their_meta_yaml_keys():
    job = RunJob(
        job_id="lca",
        kind=ProblemKind.FUNCTION,
        target=TWO_SUM_JOB.target,
        names=FunctionNames("lca", {"root": "root", "p": "p"}),
        signature=FunctionSignature(
            "lca",
            (Param("root", TREE), Param("p", TREE, ref_of="root")),
            Returns(TREE, serialize_as=NodeSerialization.INDEX, index_of="root", no_alias_with="p"),
        ),
        cases=(),
    )
    assert encoded_job(job)["signature"] == {
        "function": {
            "name": "lca",
            "params": [
                {"name": "root", "type": "TreeNode"},
                {"name": "p", "type": "TreeNode", "ref_of": "root"},
            ],
            "returns": {"type": "TreeNode", "as": "index", "of": "root", "no_alias_with": "p"},
        }
    }


def test_encodes_output_from():
    job = RunJob(
        job_id="rotate",
        kind=ProblemKind.FUNCTION,
        target=TWO_SUM_JOB.target,
        names=FunctionNames("rotate", {"nums": "nums"}),
        signature=FunctionSignature(
            "rotate", (Param("nums", INT_ARRAY),), Returns(VoidType(), output_from="nums")
        ),
        cases=(),
    )
    assert encoded_job(job)["signature"] == {
        "function": {
            "name": "rotate",
            "params": [{"name": "nums", "type": "int[]"}],
            "returns": {"type": "void", "output_from": "nums"},
        }
    }


def test_request_never_carries_hang_guards():
    assert "hang_guard_ms" not in json.dumps(encode_request(RunRequest((TWO_SUM_JOB,))))


def test_duplicate_job_ids_are_rejected():
    with pytest.raises(ValueError, match='duplicate job id "two-sum"'):
        RunRequest((TWO_SUM_JOB, TWO_SUM_JOB))


def test_decodes_hello():
    line = event_line(event="hello", runner="python", protocol=1, runtime="3.13.2")
    assert decode_event(line) == Hello("python", 1, "3.13.2")


@pytest.mark.parametrize(
    ("line", "event"),
    [
        (event_line(event="job_start", job_id="j"), JobStart("j")),
        (event_line(event="case_start", job_id="j", case_id="c"), CaseStart("j", "c")),
        (event_line(event="job_end", job_id="j"), JobEnd("j")),
        (event_line(event="bye"), Bye()),
    ],
)
def test_decodes_progress_events(line, event):
    assert decode_event(line) == event


def test_decodes_ok_result():
    line = event_line(
        event="case_result",
        job_id="j",
        case_id="c",
        status="ok",
        output=[1, 2],
        duration_ns=41000,
        stdout="",
    )
    assert decode_event(line) == CaseResult("j", "c", Returned([1, 2], 41000, ""))


def test_decodes_null_output():
    line = event_line(
        event="case_result", job_id="j", case_id="c", status="ok", output=None, duration_ns=1
    )
    assert decode_event(line) == CaseResult("j", "c", Returned(None, 1))


def test_decodes_function_error():
    error = {"type": "IndexError", "message": "list index out of range", "trace": "x.py:7"}
    line = event_line(
        event="case_result",
        job_id="j",
        case_id="c",
        status="error",
        error=error,
        duration_ns=12000,
        stdout="debug\n",
    )
    assert decode_event(line) == CaseResult(
        "j",
        "c",
        Raised(UserError("IndexError", "list index out of range", "x.py:7"), 12000, "debug\n"),
    )


def test_decodes_operation_error():
    line = event_line(
        event="case_result",
        job_id="j",
        case_id="c",
        status="error",
        error={"type": "Error", "message": "boom"},
        duration_ns=5,
        stdout="",
        op_index=3,
        partial_output=[None, 1, 2],
    )
    assert decode_event(line) == CaseResult(
        "j", "c", Raised(UserError("Error", "boom"), 5, "", 3, (None, 1, 2))
    )


def test_decodes_invalid_output():
    line = event_line(
        event="case_result",
        job_id="j",
        case_id="c",
        status="invalid_output",
        reason="list too long or cyclic",
        duration_ns=7,
        stdout="",
    )
    assert decode_event(line) == CaseResult("j", "c", InvalidOutput("list too long or cyclic", 7))


def test_decodes_load_error():
    line = event_line(
        event="load_error", job_id="j", error={"type": "ImportError", "message": "no module"}
    )
    assert decode_event(line) == LoadError("j", UserError("ImportError", "no module"))


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("not json", "not JSON"),
        ("[1]", "not a JSON object"),
        (event_line(event="wave"), 'unknown event "wave"'),
        (event_line(job_id="j"), 'missing "event"'),
        (event_line(event="job_start"), 'missing "job_id"'),
        (event_line(event="job_start", job_id=3), '"job_id" must be a string'),
        (
            event_line(event="hello", runner="python", protocol=True, runtime="3"),
            '"protocol" must be an integer',
        ),
        (
            event_line(event="case_result", job_id="j", case_id="c", status="maybe"),
            'unknown case status "maybe"',
        ),
        (
            event_line(event="load_error", job_id="j", error="boom"),
            '"error" must be an object',
        ),
    ],
)
def test_malformed_events_are_protocol_errors(line, message):
    with pytest.raises(RunnerProtocolError, match=message):
        decode_event(line)
