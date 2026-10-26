"""The real Python runner, prepared by the adapter and driven by SubprocessRunner.

The workspace is a temporary directory whose interpreter is a shim: the CLI's
own Python with runners/python/src on its path, so the test does not depend on `uv sync` having
run in a workspace. Comparators do not exist yet, so a `pass` expectation is checked as an
`ok` status whose raw output equals the case's expected value.
"""

import sys
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import (
    conformance_repository,
)
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.python import create_runner, create_stub_generator
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import (
    BuildScope,
    Prepared,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.cases import Case, FunctionInput, JsonValue, OperationSequence
from coding_study.domain.config import Config
from coding_study.domain.conformance import (
    ConformanceExpectation,
    ExpectedOutcome,
    ExpectedStatus,
)
from coding_study.domain.layout import (
    reference_file_name,
    reference_target,
    stub_path,
    user_target,
)
from coding_study.domain.naming import SymbolNames, symbol_names
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import (
    CaseOutcome,
    InvalidOutput,
    JobReport,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    TimedOut,
)
from tests.helpers import REPOSITORY_ROOT, sequential_conformance_suite
from tests.stub_contract import STUB_CASES

pytestmark = pytest.mark.slow

PYTHON = Language.PYTHON
RUNNER_SOURCES = REPOSITORY_ROOT / "runners" / "python" / "src"
SUITE = sequential_conformance_suite()
FIXTURES = conformance_repository(REPOSITORY_ROOT)
EXPECTED_CASES = [
    (expectation, case)
    for expectation in SUITE.expectations
    for case in FIXTURES.load(expectation.slug).cases
]
NOT_IMPLEMENTED = "NotImplementedError"
STUB_HANG_GUARD_MS = 5_000


def job_id(expectation: ConformanceExpectation) -> str:
    return f"{expectation.slug}/{expectation.approach_id}"


def python_names(meta: ProblemMeta) -> SymbolNames:
    return symbol_names(meta.signature, PYTHON)


def run_case(case: Case, meta: ProblemMeta) -> RunCase:
    assert isinstance(case.input, FunctionInput | OperationSequence)
    hang_guard_ms = resolve_hang_guard_ms(Config(), case.hang_guard_ms, meta.hang_guard_ms)
    return RunCase(case.id, case.input, hang_guard_ms)


def reference_source(expectation: ConformanceExpectation, meta: ProblemMeta) -> ReferenceSource:
    approach = expectation.approach_id
    solutions = REPOSITORY_ROOT / SUITE.problems_directory / meta.directory_name / "solutions"
    return ReferenceSource(approach, solutions / reference_file_name(approach, PYTHON))


def prepared_launch(root: Path, scope: BuildScope) -> RunnerLaunch:
    result = create_runner(LanguageContext(root, root / "runners")).prepare(scope, print)
    assert isinstance(result, Prepared)
    return result.launch


def run(root: Path, launch: RunnerLaunch, jobs: list[RunJob]) -> RunReport:
    return SubprocessRunner(root / ".cs" / "runs").run(launch, RunRequest(tuple(jobs)))


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("repository")
    interpreter = root / "python" / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        f'#!/bin/sh\nPYTHONPATH="{RUNNER_SOURCES}" exec "{sys.executable}" "$@"\n'
    )
    interpreter.chmod(0o755)
    return root


@pytest.fixture(scope="module")
def conformance_report(root: Path) -> RunReport:
    """Every fixture's Python reference in one request, as `cstudy verify --conformance` does."""
    jobs: list[RunJob] = []
    launches: set[RunnerLaunch] = set()
    for expectation in SUITE.expectations:
        problem = FIXTURES.load(expectation.slug)
        meta = problem.meta
        source = reference_source(expectation, meta)
        launches.add(prepared_launch(root, References(meta, (source,))))
        target = reference_target(meta, expectation.approach_id, PYTHON, str(root))
        cases = tuple(run_case(case, meta) for case in problem.cases)
        names = python_names(meta)
        jobs.append(RunJob(job_id(expectation), meta.kind, target, names, meta.signature, cases))
    (launch,) = launches
    return run(root, launch, jobs)


def outcome_of(job: JobReport, case_id: str) -> CaseOutcome:
    return next(report.outcome for report in job.cases if report.case_id == case_id)


def observed(outcome: CaseOutcome) -> dict[str, object]:
    match outcome:
        case Returned(output, _, stdout):
            return {"status": ExpectedStatus.PASS, "output": output, "stdout": stdout}
        case Raised(error, _, _, op_index, partial_output):
            return {
                "status": ExpectedStatus.ERROR,
                "message": error.message,
                "op_index": op_index,
                "partial_output": partial_output,
            }
        case InvalidOutput():
            return {"status": ExpectedStatus.INVALID_OUTPUT}
        case TimedOut():
            return {"status": ExpectedStatus.TIMEOUT}
        case _:
            return {"status": outcome}


def wanted(expected: ExpectedOutcome, case: Case) -> dict[str, object]:
    """The observed fields an expectation pins down; fields it leaves unset are not checked."""
    fields: dict[str, object] = {"status": expected.status}
    if expected.status is ExpectedStatus.PASS:
        assert case.expected is not None
        fields["output"] = case.expected.value
    optional = {
        "stdout": expected.stdout,
        "message": expected.message,
        "op_index": expected.op_index,
        "partial_output": expected.partial_output,
    }
    return fields | {key: value for key, value in optional.items() if value is not None}


@pytest.mark.parametrize(
    ("expectation", "case"),
    EXPECTED_CASES,
    ids=[f"{job_id(expectation)}/{case.id}" for expectation, case in EXPECTED_CASES],
)
def test_conformance_reference_behaves_as_expected(conformance_report, expectation, case):
    job = conformance_report.job(job_id(expectation))
    expected = expectation.outcome_for(case.id)
    if expected.status is ExpectedStatus.LOAD_ERROR:
        assert (job.load_error is not None, job.cases) == (True, ())
        return
    fields = wanted(expected, case)
    actual = observed(outcome_of(job, case.id))
    assert {key: actual.get(key) for key in fields} == fields


def test_the_report_names_the_python_runner(conformance_report):
    assert conformance_report.runner.runner == "python"


@pytest.fixture(scope="module")
def stub_root(root: Path) -> Path:
    """`root` with the generated stub of every stub case at its workspace path."""
    generator = create_stub_generator()
    for stub_case in STUB_CASES:
        stub = root / stub_path(stub_case.meta, PYTHON)
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(generator.generate(stub_case.meta))
    return root


def stub_job(root: Path, name: str, cases: tuple[RunCase, ...]) -> RunJob:
    meta = next(case.meta for case in STUB_CASES if case.name == name)
    target = user_target(meta, PYTHON, str(root))
    model = meta.concurrency.model_for(PYTHON) if meta.concurrency else None
    return RunJob(name, meta.kind, target, python_names(meta), meta.signature, cases, model)


def run_stubs(root: Path, jobs: list[RunJob]) -> RunReport:
    return run(root, prepared_launch(root, UserCode(STUB_CASES[0].meta)), jobs)


@pytest.fixture(scope="module")
def stub_report(stub_root: Path) -> RunReport:
    """Every stub loaded with no cases, so only loading can fail."""
    return run_stubs(stub_root, [stub_job(stub_root, case.name, ()) for case in STUB_CASES])


@pytest.mark.parametrize("name", [case.name for case in STUB_CASES])
def test_every_generated_stub_loads(stub_report, name):
    assert stub_report.job(name).load_error is None


def stub_outcome(root: Path, name: str, case_input: FunctionInput | OperationSequence):
    job = stub_job(root, name, (RunCase("only", case_input, STUB_HANG_GUARD_MS),))
    return run_stubs(root, [job]).job(name).cases[0].outcome


def test_a_function_stub_raises_not_implemented(stub_root):
    outcome = stub_outcome(stub_root, "two-sum", FunctionInput({"nums": [1, 2], "target": 3}))
    assert isinstance(outcome, Raised)
    assert outcome.error.type == NOT_IMPLEMENTED


def test_a_class_stub_constructs_then_fails_at_the_first_method(stub_root):
    args: tuple[tuple[JsonValue, ...], ...] = ((2,), (1,))
    outcome = stub_outcome(stub_root, "lru-cache", OperationSequence(("LRUCache", "get"), args))
    assert isinstance(outcome, Raised)
    assert (outcome.error.type, outcome.op_index, outcome.partial_output) == (
        NOT_IMPLEMENTED,
        1,
        (None,),
    )
