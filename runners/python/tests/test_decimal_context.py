"""A case that changes the decimal context must not change the next one.

See docs/specs/runners.md#execution-environment.
"""

from tests.runner_harness import function_job, run_jobs, write_source

DECIMAL_ECHO_SIGNATURE = {
    "function": {
        "name": "echo",
        "params": [{"name": "value", "type": "decimal"}],
        "returns": {"type": "decimal"},
    }
}
CONTEXT_SPOILER = """
from decimal import Decimal, getcontext


def echo(value):
    seen = getcontext().prec
    getcontext().prec = 3
    return Decimal(seen)
"""


def decimal_case(case_id: str) -> dict[str, object]:
    return {"id": case_id, "input": {"value": "1"}}


def test_every_case_starts_with_a_fresh_decimal_context(tmp_path):
    path = write_source(tmp_path, CONTEXT_SPOILER)
    cases = [decimal_case("first"), decimal_case("second"), decimal_case("third")]
    run = run_jobs(tmp_path, function_job(path, cases, DECIMAL_ECHO_SIGNATURE))
    outputs = [result["output"] for result in run.named("case_result")]
    assert outputs == ["28", "28", "28"]
