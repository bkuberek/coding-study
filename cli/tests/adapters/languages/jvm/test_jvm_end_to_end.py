"""The real JVM toolchain: Gradle builds, `cs.runner.Main` and `SubprocessRunner` together.

Marked `slow` (Gradle and a JVM per case group); `pytest -m "not slow"` deselects them. Every
test works in a temporary workspace: a copy of the practice workspace's `jvm` without sources or
build outputs, sharing its runner runtime.
"""

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import (
    conformance_repository,
)
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm import (
    create_java_stub_generator,
    create_kotlin_stub_generator,
)
from coding_study.adapters.languages.jvm.gradle import WrapperGradle, default_gradle_user_home
from coding_study.adapters.languages.jvm.runner import JvmRunner
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import (
    BuildFailed,
    Prepared,
    PrepareResult,
    References,
    ReferenceSource,
    UserCode,
)
from coding_study.domain.cases import Case, FunctionInput, OperationSequence
from coding_study.domain.conformance import ConformanceExpectation, ExpectedOutcome, ExpectedStatus
from coding_study.domain.layout import (
    reference_file_name,
    reference_target,
    stub_path,
    user_target,
)
from coding_study.domain.naming import symbol_names
from coding_study.domain.precedence import DEFAULT_HANG_GUARD_MS, first_set
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
    RunTarget,
    TimedOut,
)
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType, parse_value_type
from tests.helpers import REPOSITORY_ROOT, RUNNER_TRUNCATION_NOTICE, sequential_conformance_suite
from tests.stub_contract import STUB_CASES
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

JVM_LANGUAGES = (Language.JAVA, Language.KOTLIN)
SUITE = sequential_conformance_suite()
FIXTURES = conformance_repository(REPOSITORY_ROOT)
TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
BROKEN = replace(TWO_SUM, slug="broken-build")
DEEP_RECURSION = replace(
    TWO_SUM,
    slug="deep-recursion",
    signature=FunctionSignature(
        "depth", (Param("n", ScalarType(Scalar.INT)),), Returns(ScalarType(Scalar.INT))
    ),
)
DEEP_RECURSION_SOURCE = """package practice.deep_recursion;

public class Solution {
    public int depth(int n) {
        return n == 0 ? 0 : 1 + depth(n - 1);
    }
}
"""
LOUD = replace(DEEP_RECURSION, slug="loud")
LOUD_SOURCE = """package practice.loud;

public class Solution {
    public int depth(int n) {
        System.out.print("x".repeat(n));
        return n;
    }
}
"""
OUTPUT_LIMIT_BYTES = 4096
RECURSION_DEPTH = 200_000
"""Far beyond a default 1 MiB thread stack; fits the runner's 256 MiB case stack."""
NOT_IMPLEMENTED = {
    Language.JAVA: "UnsupportedOperationException",
    Language.KOTLIN: "NotImplementedError",
}
BROKEN_SOURCES = {
    Language.JAVA: "package practice.broken_build;\n\npublic class Solution {\n    int x = ;\n}\n",
    Language.KOTLIN: "package practice.broken_build\n\nclass Solution {\n    val x: Int = \n}\n",
}


@dataclass(frozen=True, slots=True)
class Behavior:
    """A one-parameter Java function of `type_text` whose body is `body`."""

    slug: str
    type_text: str
    body: str

    @property
    def meta(self) -> ProblemMeta:
        declared = parse_value_type(self.type_text)
        signature = FunctionSignature("behave", (Param("value", declared),), Returns(declared))
        return replace(TWO_SUM, slug=self.slug, signature=signature)

    @property
    def source(self) -> str:
        package = self.slug.replace("-", "_")
        java_type = {"decimal": "BigDecimal", "date": "LocalDate"}[self.type_text]
        return (
            f"package practice.{package};\n\n"
            "import java.math.BigDecimal;\nimport java.time.LocalDate;\n\n"
            f"public class Solution {{\n    public {java_type} behave({java_type} value) {{\n"
            f"        {self.body}\n    }}\n}}\n"
        )


NULL_DECIMAL = Behavior("null-decimal", "decimal", "return null;")
NULL_DATE = Behavior("null-date", "date", "return null;")
FAR_FUTURE = Behavior("far-future", "date", "return LocalDate.of(10000, 1, 1);")
YEAR_ZERO = Behavior("year-zero", "date", "return LocalDate.of(0, 1, 1);")
PADDED_DECIMAL = Behavior("padded-decimal", "decimal", "return value.setScale(4);")
EXPONENT_DECIMAL = Behavior("exponent-decimal", "decimal", 'return new BigDecimal("1E+2");')
STUB_GENERATORS = {
    Language.JAVA: create_java_stub_generator(),
    Language.KOTLIN: create_kotlin_stub_generator(),
}


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("jvm-root") / "ws")


def runner(root: Path, language: Language) -> JvmRunner:
    gradle = WrapperGradle(root / "jvm", default_gradle_user_home())
    return JvmRunner(LanguageContext(root, root / RUNTIME_RUNNERS), language, gradle)


def launched(result: PrepareResult) -> Prepared:
    assert isinstance(result, Prepared), result
    return result


def run_cases(
    root: Path, result: PrepareResult, meta: ProblemMeta, language: Language, target: RunTarget
) -> JobReport:
    cases = FIXTURES.load(meta.slug).cases if meta.slug.startswith("conformance") else ()
    job = RunJob(
        job_id=meta.slug,
        kind=meta.kind,
        target=target,
        names=symbol_names(meta.signature, language),
        signature=meta.signature,
        cases=tuple(run_case(case, meta) for case in cases),
    )
    report = SubprocessRunner(root / ".cs" / "runs").run(
        launched(result).launch, RunRequest((job,))
    )
    return report.job(meta.slug)


def run_case(case: Case, meta: ProblemMeta) -> RunCase:
    assert isinstance(case.input, FunctionInput | OperationSequence)
    hang_guard_ms = first_set(case.hang_guard_ms, meta.hang_guard_ms, default=DEFAULT_HANG_GUARD_MS)
    return RunCase(case.id, case.input, hang_guard_ms)


def matches(expected: ExpectedOutcome, outcome: CaseOutcome, case: Case) -> bool:
    match expected.status, outcome:
        case ExpectedStatus.PASS, Returned(output=output, stdout=stdout):
            expected_stdout = stdout if expected.stdout is None else expected.stdout
            return (
                case.expected is not None
                and output == case.expected.value
                and stdout == expected_stdout
            )
        case ExpectedStatus.ERROR, Raised(error=error, op_index=op_index, partial_output=partial):
            return (
                expected.message in (None, error.message)
                and expected.op_index in (None, op_index)
                and expected.partial_output in (None, partial)
            )
        case ExpectedStatus.INVALID_OUTPUT, InvalidOutput():
            return True
        case ExpectedStatus.TIMEOUT, TimedOut():
            return True
        case _:
            return False


def mismatches(expectation: ConformanceExpectation, job: JobReport) -> dict[str, object]:
    cases = {case.id: case for case in FIXTURES.load(expectation.slug).cases}
    if expectation.outcome.status is ExpectedStatus.LOAD_ERROR:
        return {} if job.load_error is not None and not job.cases else {"job": job}
    return {
        report.case_id: report.outcome
        for report in job.cases
        if not matches(
            expectation.outcome_for(report.case_id), report.outcome, cases[report.case_id]
        )
    }


@pytest.mark.parametrize("language", JVM_LANGUAGES)
@pytest.mark.parametrize(
    "expectation", SUITE.expectations, ids=lambda e: f"{e.slug}/{e.approach_id}"
)
def test_conformance_reference_produces_the_expected_outcomes(root, language, expectation):
    meta = FIXTURES.load(expectation.slug).meta
    solutions = REPOSITORY_ROOT / SUITE.problems_directory / meta.directory_name / "solutions"
    source = ReferenceSource(
        expectation.approach_id, solutions / reference_file_name(expectation.approach_id, language)
    )
    result = runner(root, language).prepare(References(meta, (source,)), lambda _notice: None)
    target = reference_target(meta, expectation.approach_id, language, str(root))
    job = run_cases(root, result, meta, language, target)
    assert len(job.cases) == len(FIXTURES.load(meta.slug).cases) or job.load_error is not None
    assert mismatches(expectation, job) == {}


@pytest.fixture
def user_stub(root: Path) -> Iterator[None]:
    for language in JVM_LANGUAGES:
        path = root / stub_path(TWO_SUM, language)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(STUB_GENERATORS[language].generate(TWO_SUM))
    yield
    for language in JVM_LANGUAGES:
        shutil.rmtree((root / stub_path(TWO_SUM, language)).parent)


@pytest.fixture
def broken_file(root: Path) -> Iterator[None]:
    for language in JVM_LANGUAGES:
        path = root / stub_path(BROKEN, language)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BROKEN_SOURCES[language])
    yield
    for language in JVM_LANGUAGES:
        shutil.rmtree((root / stub_path(BROKEN, language)).parent)


def user_report(root: Path, meta: ProblemMeta, language: Language, case: RunCase) -> RunReport:
    result = runner(root, language).prepare(UserCode(meta), lambda _notice: None)
    job = RunJob(
        meta.slug,
        meta.kind,
        user_target(meta, language, str(root)),
        symbol_names(meta.signature, language),
        meta.signature,
        (case,),
    )
    return SubprocessRunner(root / ".cs" / "runs").run(launched(result).launch, RunRequest((job,)))


def two_sum_report(root: Path, language: Language) -> RunReport:
    case = RunCase("ex1", FunctionInput({"nums": [2, 7], "target": 9}), DEFAULT_HANG_GUARD_MS)
    return user_report(root, TWO_SUM, language, case)


@pytest.fixture
def deep_recursion(root: Path) -> Iterator[None]:
    path = root / stub_path(DEEP_RECURSION, Language.JAVA)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEEP_RECURSION_SOURCE)
    yield
    shutil.rmtree(path.parent)


@pytest.mark.usefixtures("deep_recursion")
def test_cases_run_on_a_stack_deep_enough_for_heavy_recursion(root):
    case = RunCase("deep", FunctionInput({"n": RECURSION_DEPTH}), DEFAULT_HANG_GUARD_MS)
    report = user_report(root, DEEP_RECURSION, Language.JAVA, case)
    outcome = report.job(DEEP_RECURSION.slug).cases[0].outcome
    output = outcome.output if isinstance(outcome, Returned) else outcome
    assert output == RECURSION_DEPTH


@contextmanager
def written(root: Path, behavior: Behavior) -> Iterator[None]:
    path = root / stub_path(behavior.meta, Language.JAVA)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(behavior.source)
    try:
        yield
    finally:
        shutil.rmtree(path.parent)


def behavior_outcome(root: Path, behavior: Behavior, value: str) -> CaseOutcome:
    case = RunCase("c", FunctionInput({"value": value}), DEFAULT_HANG_GUARD_MS)
    with written(root, behavior):
        report = user_report(root, behavior.meta, Language.JAVA, case)
    return report.job(behavior.slug).cases[0].outcome


@pytest.mark.parametrize(
    ("behavior", "value"),
    [
        (NULL_DECIMAL, "2500.00"),
        (NULL_DATE, "2024-02-29"),
        (FAR_FUTURE, "2024-02-29"),
        (YEAR_ZERO, "2024-02-29"),
    ],
    ids=lambda item: item.slug if isinstance(item, Behavior) else "",
)
def test_a_decimal_or_date_the_runner_cannot_encode_is_invalid_output(root, behavior, value):
    assert isinstance(behavior_outcome(root, behavior, value), InvalidOutput)


@pytest.mark.parametrize(
    ("behavior", "value", "canonical"),
    [
        (PADDED_DECIMAL, "2500.5", "2500.5"),
        (PADDED_DECIMAL, "0.00", "0"),
        (PADDED_DECIMAL, "-0", "0"),
        (EXPONENT_DECIMAL, "1", "100"),
    ],
    ids=lambda item: item.slug if isinstance(item, Behavior) else "",
)
def test_a_decimal_output_is_written_in_canonical_form(root, behavior, value, canonical):
    outcome = behavior_outcome(root, behavior, value)
    assert (outcome.output if isinstance(outcome, Returned) else outcome) == canonical


@pytest.fixture
def loud(root: Path) -> Iterator[None]:
    path = root / stub_path(LOUD, Language.JAVA)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LOUD_SOURCE)
    yield
    shutil.rmtree(path.parent)


@pytest.mark.usefixtures("loud")
def test_output_over_4_kib_is_truncated_with_the_shared_notice(root):
    case = RunCase("loud", FunctionInput({"n": 5000}), DEFAULT_HANG_GUARD_MS)
    outcome = user_report(root, LOUD, Language.JAVA, case).job(LOUD.slug).cases[0].outcome
    stdout = outcome.stdout if isinstance(outcome, Returned) else outcome
    assert stdout == "x" * OUTPUT_LIMIT_BYTES + RUNNER_TRUNCATION_NOTICE


@pytest.mark.usefixtures("user_stub")
@pytest.mark.parametrize("language", JVM_LANGUAGES)
def test_generated_stub_runs_and_reports_not_implemented(root, language):
    outcome = two_sum_report(root, language).job("two-sum").cases[0].outcome
    raised_type = outcome.error.type if isinstance(outcome, Raised) else None
    assert raised_type == NOT_IMPLEMENTED[language]


@pytest.mark.usefixtures("broken_file")
@pytest.mark.parametrize("language", JVM_LANGUAGES)
def test_compile_error_is_a_build_failure_naming_the_file(root, language):
    result = runner(root, language).prepare(UserCode(BROKEN), lambda _notice: None)
    diagnostics = result.diagnostics if isinstance(result, BuildFailed) else ()
    assert any("practice/broken_build/Solution." in line for line in diagnostics)


@pytest.mark.usefixtures("user_stub", "broken_file")
@pytest.mark.parametrize("language", JVM_LANGUAGES)
def test_broken_file_of_another_problem_does_not_block_the_build(root, language):
    assert two_sum_report(root, language).runner.runner == "jvm"


def test_every_golden_stub_compiles(root):
    for case in STUB_CASES:
        for language in JVM_LANGUAGES:
            path = root / stub_path(case.meta, language)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(STUB_GENERATORS[language].generate(case.meta))
    gradle = WrapperGradle(root / "jvm", default_gradle_user_home())
    outcome = gradle.run(["-q", "--console=plain", ":java:classes", ":kotlin:classes"])
    for case in STUB_CASES:
        for language in JVM_LANGUAGES:
            shutil.rmtree((root / stub_path(case.meta, language)).parent, ignore_errors=True)
    assert outcome.exit_code == 0, outcome.output


# Two `cstudy` processes on one workspace share the reference build's output directories.

RACE_APPROACH = "hash-map"
RACE_SOURCES = {Language.JAVA: "public class Solution {\n}\n", Language.KOTLIN: "class Solution\n"}
CLASSPATH_FLAG = "-cp"


def race_references(directory: Path, meta: ProblemMeta, language: Language) -> References:
    source = directory / meta.slug / reference_file_name(RACE_APPROACH, language)
    source.parent.mkdir(parents=True)
    source.write_text(RACE_SOURCES[language])
    return References(meta, (ReferenceSource(RACE_APPROACH, source),))


def prepared_classes(result: PrepareResult, meta: ProblemMeta) -> list[Path]:
    """The class files of the reference approach that the prepared launch can load."""
    command = launched(result).launch.command
    entries = command[command.index(CLASSPATH_FLAG) + 1].split(os.pathsep)
    relative = Path("ref", meta.snake_slug, RACE_APPROACH.replace("-", "_"), "Solution.class")
    return [Path(entry) / relative for entry in entries if (Path(entry) / relative).is_file()]


@pytest.mark.parametrize("language", JVM_LANGUAGES)
def test_a_build_for_another_problem_leaves_prepared_classes_loadable(root, tmp_path, language):
    alpha = replace(TWO_SUM, slug="race-alpha")
    beta = replace(TWO_SUM, slug="race-beta")
    first = runner(root, language).prepare(
        race_references(tmp_path, alpha, language), lambda _notice: None
    )
    runner(root, language).prepare(race_references(tmp_path, beta, language), lambda _notice: None)
    assert prepared_classes(first, alpha) != []
