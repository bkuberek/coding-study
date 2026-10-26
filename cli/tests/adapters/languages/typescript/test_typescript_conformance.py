"""The real TypeScript runner on the conformance fixtures (runners/conformance/README.md).

Every TypeScript reference runs in one runner process through `SubprocessRunner`, as
`cstudy verify --conformance` will run them. Comparators do not exist yet, so a `pass` expectation
asserts the raw output equals the case's expected value (every fixture uses exact values).
"""

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.conformance_fixtures import (
    conformance_repository,
)
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.typescript import create_runner
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import Prepared, References, ReferenceSource
from coding_study.domain.cases import Case, GeneratedInput
from coding_study.domain.config import Config
from coding_study.domain.conformance import ConformanceExpectation, ExpectedOutcome, ExpectedStatus
from coding_study.domain.layout import reference_file_name, reference_target
from coding_study.domain.naming import symbol_names
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, Problem
from coding_study.domain.runs import (
    CaseOutcome,
    InvalidOutput,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    TimedOut,
)
from coding_study.domain.stress import StressScenario
from tests.helpers import REPOSITORY_ROOT, sequential_conformance_suite

TYPESCRIPT = Language.TYPESCRIPT
SUITE = sequential_conformance_suite()
REPOSITORY = conformance_repository(REPOSITORY_ROOT)
DIRECTORIES = {summary.meta.slug: summary.directory for summary in REPOSITORY.list_summaries()}

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]


def job_id(expectation: ConformanceExpectation) -> str:
    return f"{expectation.slug}/{expectation.approach_id}"


def case_parameters() -> Iterator[Any]:
    for expectation in SUITE.expectations:
        if expectation.outcome.status is ExpectedStatus.LOAD_ERROR:
            continue
        for case in REPOSITORY.load(expectation.slug).cases:
            yield pytest.param(expectation, case, id=f"{job_id(expectation)}/{case.id}")


def run_job(expectation: ConformanceExpectation, problem: Problem, root: Path) -> RunJob:
    meta = problem.meta
    return RunJob(
        job_id=job_id(expectation),
        kind=meta.kind,
        target=reference_target(meta, expectation.approach_id, TYPESCRIPT, str(root)),
        names=symbol_names(meta.signature, TYPESCRIPT),
        signature=meta.signature,
        cases=tuple(run_case(case, meta.hang_guard_ms) for case in problem.cases),
    )


def run_case(case: Case, meta_hang_guard_ms: int | None) -> RunCase:
    assert not isinstance(case.input, GeneratedInput | StressScenario)
    hang_guard_ms = resolve_hang_guard_ms(Config(), case.hang_guard_ms, meta_hang_guard_ms)
    return RunCase(case.id, case.input, hang_guard_ms)


@pytest.fixture(scope="module")
def report(tmp_path_factory: pytest.TempPathFactory) -> RunReport:
    root = tmp_path_factory.mktemp("repository")
    (root / "runners").symlink_to(REPOSITORY_ROOT / "runners")
    runner = create_runner(LanguageContext(root, root / "runners"))
    jobs: list[RunJob] = []
    launch = None
    for expectation in SUITE.expectations:
        problem = REPOSITORY.load(expectation.slug)
        solutions = REPOSITORY_ROOT / DIRECTORIES[expectation.slug] / "solutions"
        path = solutions / reference_file_name(expectation.approach_id, TYPESCRIPT)
        scope = References(problem.meta, (ReferenceSource(expectation.approach_id, path),))
        prepared = runner.prepare(scope, print)
        assert isinstance(prepared, Prepared)
        launch = prepared.launch
        jobs.append(run_job(expectation, problem, root))
    assert launch is not None
    return SubprocessRunner(root / ".cs" / "runs").run(launch, RunRequest(tuple(jobs)))


def observed(outcome: CaseOutcome) -> dict[str, Any]:
    match outcome:
        case Returned(output=output, stdout=stdout):
            return {"status": ExpectedStatus.PASS, "output": output, "stdout": stdout}
        case Raised(error=error, op_index=op_index, partial_output=partial_output):
            return {
                "status": ExpectedStatus.ERROR,
                "message": error.message,
                "op_index": op_index,
                "partial_output": list(partial_output),
                "type": error.type,
            }
        case InvalidOutput(reason=reason):
            return {"status": ExpectedStatus.INVALID_OUTPUT, "reason": reason}
        case TimedOut():
            return {"status": ExpectedStatus.TIMEOUT}
        case _:
            return {"status": repr(outcome)}


def expected_fields(expected: ExpectedOutcome, case: Case) -> dict[str, Any]:
    """The fields `expected` constrains; a pass also fixes the output to the case's value."""
    partial_output = None if expected.partial_output is None else list(expected.partial_output)
    output = case.expected.value if case.expected is not None else None
    fields: dict[str, Any] = {
        "status": expected.status,
        "output": output if expected.status is ExpectedStatus.PASS else None,
        "stdout": expected.stdout,
        "message": expected.message,
        "op_index": expected.op_index,
        "partial_output": partial_output,
    }
    return {key: value for key, value in fields.items() if value is not None}


@pytest.mark.parametrize(("expectation", "case"), list(case_parameters()))
def test_case_outcome_matches_the_expectation(report, expectation, case):
    expected = expectation.outcome_for(case.id)
    job = report.job(job_id(expectation))
    outcome = next(entry.outcome for entry in job.cases if entry.case_id == case.id)
    wanted, actual = expected_fields(expected, case), observed(outcome)
    assert {key: actual.get(key) for key in wanted} == wanted, actual


@pytest.mark.parametrize(
    "expectation",
    [e for e in SUITE.expectations if e.outcome.status is ExpectedStatus.LOAD_ERROR],
    ids=job_id,
)
def test_job_reports_a_load_error(report, expectation):
    assert report.job(job_id(expectation)).load_error is not None


def test_runner_identifies_itself(report):
    assert report.runner.runner == "typescript"
