"""The wire format of suite jobs (docs/specs/runners.md#suite-job)."""

import json
from dataclasses import replace
from typing import Any, cast

import pytest

from coding_study.adapters.runner_protocol import CaseResult, decode_event, encode_suite_request
from coding_study.domain.errors import RunnerProtocolError
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Comparison,
    Passed,
    Skipped,
    SuiteFramework,
    SuiteJob,
)

SUITE = SuiteJob(
    job_id="bank-project-python/suite",
    framework=SuiteFramework.PYTEST,
    root="/home/me/ws/projects/bank-project-python",
    hang_guard_ms=10_000,
    exclude=("tests/test_level_2.py",),
)


def encoded_job(job: SuiteJob, skip: tuple[str, ...] = ()) -> dict[str, Any]:
    jobs = cast("list[dict[str, Any]]", encode_suite_request(job, skip)["jobs"])
    return jobs[0]


def event_line(**fields: Any) -> str:
    return json.dumps(fields)


def result_line(status: str, **fields: Any) -> str:
    return event_line(
        event="case_result",
        job_id="j",
        case_id="tests/test_level_1.py::test_ex1",
        status=status,
        duration_ns=5,
        **fields,
    )


def test_encodes_the_spec_example_suite_request():
    assert encode_suite_request(SUITE, skip=()) == {
        "protocol": 1,
        "mode": "test",
        "jobs": [
            {
                "job_id": "bank-project-python/suite",
                "kind": "suite",
                "framework": "pytest",
                "root": "/home/me/ws/projects/bank-project-python",
                "exclude": ["tests/test_level_2.py"],
                "select": [],
                "skip": [],
            }
        ],
    }


def test_encodes_the_tests_to_select():
    assert encoded_job(replace(SUITE, select=("test_ex1",)))["select"] == ["test_ex1"]


def test_encodes_the_tests_a_restart_skips_in_order():
    skip = ("tests/test_a.py::test_b", "tests/test_a.py::test_a")
    assert encoded_job(SUITE, skip)["skip"] == list(skip)


def test_never_sends_the_hang_guard():
    assert "hang_guard_ms" not in encoded_job(SUITE)


def test_encodes_node_test_by_its_protocol_name():
    job = SuiteJob("j", SuiteFramework.NODE_TEST, "/root", 10_000)
    assert encoded_job(job)["framework"] == "node-test"


def test_an_ok_result_without_an_output_is_a_passed_test():
    decoded = decode_event(result_line("ok", stdout="hi\n"))
    assert decoded == CaseResult("j", "tests/test_level_1.py::test_ex1", Passed(5, "hi\n"))


def test_decodes_a_failed_assertion_with_the_frameworks_message():
    decoded = decode_event(result_line("failed", message="assert -1 == 5"))
    assert isinstance(decoded, CaseResult)
    assert decoded.outcome == AssertionFailed("assert -1 == 5", 5)


def test_decodes_both_sides_of_a_failed_assertion_when_reported():
    decoded = decode_event(result_line("failed", message="m", expected=[1, 2], actual=None))
    assert isinstance(decoded, CaseResult)
    assert decoded.outcome == AssertionFailed("m", 5, comparison=Comparison([1, 2], None))


def test_a_failed_assertion_with_one_side_only_is_a_protocol_error():
    with pytest.raises(RunnerProtocolError, match="expected and actual"):
        decode_event(result_line("failed", message="m", expected=1))


def test_decodes_a_skipped_test_with_its_reason():
    decoded = decode_event(result_line("skipped", message="not today"))
    assert isinstance(decoded, CaseResult)
    assert decoded.outcome == Skipped("not today", 5)
