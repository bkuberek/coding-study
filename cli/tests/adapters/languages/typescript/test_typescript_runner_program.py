"""Behavior of runners/typescript/runner.ts beyond the conformance suite, through SubprocessRunner.

All jobs run in one runner process (module fixture); each test inspects one outcome.
"""

import json
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.cases import FunctionInput, JsonValue, OperationSequence
from coding_study.domain.naming import ClassNames, FunctionNames
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.runs import (
    HELLO_TIMEOUT_MS,
    CaseOutcome,
    FileTarget,
    InvalidOutput,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    UserError,
)
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.helpers import REPOSITORY_ROOT, RUNNER_TRUNCATION_NOTICE

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

RUNNER_SCRIPT = REPOSITORY_ROOT / "runners" / "typescript" / "runner.ts"
HANG_GUARD_MS = 5_000
STDOUT_LIMIT_BYTES = 4096

BEHAVIORS = """\
export function exitsWhenNegative(value: number): number {
  if (value < 0) {
    process.exit(3);
  }
  return value;
}

export function adds(a: number, b: number): number {
  return a + b;
}

export function overflows(value: number): number {
  return 2 ** 31 + value;
}

export function forgetsReturn(head: unknown): unknown {}

export function resolvesLater(value: number): Promise<number> {
  return Promise.resolve(value);
}

export function sharesAChild(root: unknown): unknown {
  const leaf = { val: 2, left: null, right: null };
  return { val: 1, left: leaf, right: leaf };
}

export function fractionalVal(head: unknown): unknown {
  return { val: 1.5, next: null };
}

export function lonelyNodeSeven(node: unknown): unknown {
  return { val: 7, neighbors: [] };
}

export function printsALot(value: number): number {
  process.stdout.write("x".repeat(5000));
  return value;
}

export function warns(value: number): number {
  console.error("careful");
  return value;
}

function inner(value: number): number {
  throw new TypeError(`deep ${value}`);
}

export function throwsDeep(value: number): number {
  return inner(value);
}

export function throwsString(value: number): number {
  throw "plain string";
}

export function picks(head: unknown, node: unknown): unknown {
  return node;
}

export class Stack {
  push(value: number): void {}
}

export class Fragile {
  constructor() {
    throw new Error("cannot build");
  }

  size(): number {
    return 0;
  }
}
"""
UNSUPPORTED_SYNTAX = "export enum Color {\n  Red,\n}\n"
INVALID_SYNTAX = (
    "export function anything(value: number): number {\n  const x = ;\n  return x;\n}\n"
)


def line_of(text: str) -> int:
    return next(number for number, line in enumerate(BEHAVIORS.splitlines(), 1) if text in line)


def function_signature(name: str, params: Mapping[str, str], returns: Returns) -> FunctionSignature:
    declared = tuple(Param(param, parse_value_type(type_)) for param, type_ in params.items())
    return FunctionSignature(name, declared, returns)


def function_job(
    target: Path,
    name: str,
    inputs: list[dict[str, JsonValue]],
    types: tuple[str, str] = ("int", "int"),
) -> RunJob:
    """A one-parameter function; `types` are the parameter and return types."""
    param_type, return_type = types
    signature = function_signature(
        name, {"value": param_type}, Returns(parse_return_type(return_type))
    )
    return function_job_for(target, signature, inputs, job_id=name)


def function_job_for(
    target: Path, signature: FunctionSignature, inputs: list[dict[str, JsonValue]], job_id: str
) -> RunJob:
    cases = tuple(
        RunCase(f"c{index}", FunctionInput(arguments), HANG_GUARD_MS)
        for index, arguments in enumerate(inputs)
    )
    names = FunctionNames(signature.name, {param.name: param.name for param in signature.params})
    return RunJob(job_id, ProblemKind.FUNCTION, FileTarget(str(target)), names, signature, cases)


def class_job(target: Path, name: str, methods: tuple[Method, ...], ops: tuple[str, ...]) -> RunJob:
    signature = ClassSignature(name, (), methods)
    names = ClassNames(name, {method.name: method.name for method in methods})
    sequence = OperationSequence(ops, tuple(() for _ in ops))
    case = RunCase("c0", sequence, HANG_GUARD_MS)
    return RunJob(name, ProblemKind.DESIGN, FileTarget(str(target)), names, signature, (case,))


def jobs(behaviors: Path, project: Path) -> tuple[RunJob, ...]:
    picks = FunctionSignature(
        "picks",
        (
            Param("head", parse_value_type("ListNode")),
            Param("node", parse_value_type("ListNode"), ref_of="head"),
        ),
        Returns(parse_return_type("ListNode")),
    )
    push = Method(
        "push", (Param("value", parse_value_type("int")),), Returns(parse_return_type("void"))
    )
    pop = Method("pop", (), Returns(parse_return_type("int")))
    size = Method("size", (), Returns(parse_return_type("int")))
    anything = function_signature("anything", {"value": "int"}, Returns(parse_return_type("int")))
    return (
        function_job(behaviors, "exitsWhenNegative", [{"value": -1}, {"value": 5}]),
        function_job(behaviors, "adds", [{"value": 1}]),
        function_job(behaviors, "overflows", [{"value": 0}]),
        function_job(behaviors, "forgetsReturn", [{"value": []}], ("ListNode", "ListNode")),
        function_job(behaviors, "resolvesLater", [{"value": 1}]),
        function_job(behaviors, "sharesAChild", [{"value": []}], ("TreeNode", "TreeNode")),
        function_job(behaviors, "fractionalVal", [{"value": []}], ("ListNode", "ListNode")),
        function_job(behaviors, "lonelyNodeSeven", [{"value": []}], ("GraphNode", "GraphNode")),
        function_job(behaviors, "printsALot", [{"value": 1}]),
        function_job(behaviors, "warns", [{"value": 1}]),
        function_job(behaviors, "throwsDeep", [{"value": 4}]),
        function_job(behaviors, "throwsString", [{"value": 1}]),
        function_job(behaviors, "missingFunction", [{"value": 1}]),
        function_job_for(behaviors, picks, [{"head": [1, 2], "node": 9}], job_id="picks"),
        function_job_for(
            project / "unsupported.ts", anything, [{"value": 1}], job_id="unsupported"
        ),
        function_job_for(project / "absent.ts", anything, [{"value": 1}], job_id="absent"),
        function_job_for(project / "invalid.ts", anything, [{"value": 1}], job_id="invalid"),
        class_job(behaviors, "Stack", (push, pop), ("Stack", "push", "pop")),
        class_job(behaviors, "Fragile", (size,), ("Fragile", "size")),
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("typescript-project")
    (directory / "package.json").write_text('{"type": "module"}\n')
    (directory / "behaviors.ts").write_text(BEHAVIORS)
    (directory / "unsupported.ts").write_text(UNSUPPORTED_SYNTAX)
    (directory / "invalid.ts").write_text(INVALID_SYNTAX)
    return directory


@pytest.fixture(scope="module")
def report(project: Path) -> RunReport:
    launch = RunnerLaunch(
        ("node", str(RUNNER_SCRIPT)), project, HELLO_TIMEOUT_MS[Language.TYPESCRIPT]
    )
    request = RunRequest(jobs(project / "behaviors.ts", project))
    return SubprocessRunner(project / "runs").run(launch, request)


def outcome(report: RunReport, job_id: str, case_id: str = "c0") -> CaseOutcome:
    return next(case.outcome for case in report.job(job_id).cases if case.case_id == case_id)


def raised(report: RunReport, job_id: str) -> Raised:
    result = outcome(report, job_id)
    assert isinstance(result, Raised), result
    return result


def returned(report: RunReport, job_id: str, case_id: str = "c0") -> Returned:
    result = outcome(report, job_id, case_id)
    assert isinstance(result, Returned), result
    return result


def invalid_reason(report: RunReport, job_id: str) -> str:
    result = outcome(report, job_id)
    assert isinstance(result, InvalidOutput), result
    return result.reason


def load_error(report: RunReport, job_id: str) -> UserError:
    error = report.job(job_id).load_error
    assert error is not None
    return error


def test_hello_names_the_node_version(report):
    assert report.runner.runtime.split(".")[0] == "24"


def test_process_exit_is_a_case_error(report):
    assert raised(report, "exitsWhenNegative").error.type == "ProcessExitError"


def test_cases_after_process_exit_still_run(report):
    assert returned(report, "exitsWhenNegative", "c1").output == 5


def test_returned_case_reports_a_positive_duration(report):
    assert returned(report, "exitsWhenNegative", "c1").duration_ns > 0


def test_arity_mismatch_is_a_load_error(report):
    assert load_error(report, "adds").type == "ArityMismatch"


def test_int_beyond_32_bits_is_invalid_output(report):
    reason = invalid_reason(report, "overflows")
    assert reason == "expected an int (32-bit integer), got 2147483648"


def test_undefined_for_a_node_return_is_invalid_output(report):
    assert "got undefined" in invalid_reason(report, "forgetsReturn")


def test_promise_is_invalid_output(report):
    assert "got a Promise" in invalid_reason(report, "resolvesLater")


def test_tree_node_with_two_parents_is_invalid_output(report):
    assert "two parents" in invalid_reason(report, "sharesAChild")


def test_fractional_node_val_is_invalid_output(report):
    assert "got 1.5" in invalid_reason(report, "fractionalVal")


def test_graph_vals_must_number_the_reachable_nodes_from_one(report):
    assert "exactly 1..1" in invalid_reason(report, "lonelyNodeSeven")


def test_stdout_is_truncated_to_4_kib_with_the_shared_notice(report):
    stdout = returned(report, "printsALot").stdout
    assert stdout == "x" * STDOUT_LIMIT_BYTES + RUNNER_TRUNCATION_NOTICE


def test_console_error_is_captured_with_the_case(report):
    assert returned(report, "warns").stdout == "careful\n"


def test_error_reports_the_exception_class_and_message(report):
    error = raised(report, "throwsDeep").error
    assert (error.type, error.message) == ("TypeError", "deep 4")


def test_trace_lists_user_frames_innermost_first(report):
    trace = raised(report, "throwsDeep").error.trace.splitlines()
    inner, outer = line_of("throw new TypeError"), line_of("return inner(value)")
    assert trace == [f"behaviors.ts:{inner} in inner", f"behaviors.ts:{outer} in throwsDeep"]


def test_thrown_non_error_reports_its_javascript_type(report):
    error = raised(report, "throwsString").error
    assert (error.type, error.message) == ("string", "plain string")


def test_missing_export_is_a_load_error(report):
    assert load_error(report, "missingFunction").type == "MissingExport"


def test_missing_export_message_lists_the_exports(report):
    message = load_error(report, "missingFunction").message
    assert "(exports: Fragile, Stack, adds, exitsWhenNegative," in message


def test_unknown_ref_of_value_is_an_input_error(report):
    assert raised(report, "picks").error.type == "InvalidInput"


def test_unsupported_typescript_syntax_is_a_load_error(report):
    assert "enum" in load_error(report, "unsupported").message.lower()


def test_syntax_error_is_a_load_error(report):
    assert load_error(report, "invalid").type == "SyntaxError"


def test_syntax_error_trace_points_at_the_line_with_an_excerpt(report):
    trace = load_error(report, "invalid").trace.splitlines()
    assert trace[:3] == ["invalid.ts:2", INVALID_SYNTAX.splitlines()[0], "  const x = ;"]


def test_missing_file_is_a_load_error(report):
    assert load_error(report, "absent").type == "FileNotFound"


def test_missing_method_is_a_load_error(report):
    assert load_error(report, "Stack").type == "MissingMethod"


def test_constructor_error_is_reported_at_op_zero(report):
    result = raised(report, "Fragile")
    assert (result.op_index, result.partial_output) == (0, ())


def test_bad_request_exits_with_code_2(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"protocol": 2, "mode": "test", "jobs": []}))
    command = ["node", str(RUNNER_SCRIPT), "--request", str(request), "--out", str(tmp_path / "o")]
    assert subprocess.run(command, capture_output=True, check=False).returncode == 2
