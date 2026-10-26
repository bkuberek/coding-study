"""Turns a problem's cases into runnable ones.

Spec: docs/specs/problem-format.md#generated-cases-and-generatorpy.

Generated inputs come from generator.py; their expected values are the outputs of the
`perf.expected_from` approach run through the Python runner, cached in `.cs/cases/`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.language_runs import LanguageRun, reference_job_id
from coding_study.application.ports import ProgressNotice
from coding_study.domain.cases import Case, Expected, GeneratedInput
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.generated_cases import (
    GeneratedCase,
    OracleInput,
    expected_source,
    generated_run_input,
    materialized_case,
)
from coding_study.domain.judging import RunnableCase, concrete_case, outcome_summary
from coding_study.domain.layout import SOURCE_EXTENSIONS
from coding_study.domain.problem import Language, Problem, ProblemMeta
from coding_study.domain.problem_files import (
    GENERATOR_FILE,
    META_FILE,
    SOLUTIONS_DIRECTORY,
    TESTS_FILE,
    solution_file,
)
from coding_study.domain.runs import Returned, RunInput

EXPECTED_VALUES_NOTICE = "computing expected values for generated cases (one-time)"
ORACLE_OUTPUTS_NOTICE = "computing oracle outputs for the stress inputs (one-time)"
ORACLE_CACHE_SUFFIX = "-oracle"
"""Oracle outputs live next to the generated cases, under their own key."""


def python_approaches(environment: Environment, meta: ProblemMeta) -> frozenset[str]:
    """Approaches with a Python reference file."""
    suffix = f".{SOURCE_EXTENSIONS[Language.PYTHON]}"
    names = environment.files.file_names(meta.slug, SOLUTIONS_DIRECTORY)
    declared = {approach.id for approach in meta.approaches}
    return frozenset(
        name.removesuffix(suffix)
        for name in names
        if name.endswith(suffix) and name.removesuffix(suffix) in declared
    )


@dataclass(frozen=True, slots=True)
class _Source:
    """The approach whose Python outputs become expected values."""

    approach: str
    key: str = ""
    """Appended to the cache key."""
    notice: str = EXPECTED_VALUES_NOTICE


class CaseMaterializer:
    def __init__(self, environment: Environment, notify: ProgressNotice) -> None:
        self._environment = environment
        self._notify = notify

    def runnable_cases(self, problem: Problem) -> tuple[RunnableCase, ...]:
        """Every case in tests.json order, with generated inputs and expected values filled in."""
        generated = [case for case in problem.cases if isinstance(case.input, GeneratedInput)]
        meta = problem.meta
        values: Mapping[str, GeneratedCase] = (
            self._generated(meta, generated, _Source(self._expected_source(meta)))
            if generated
            else {}
        )
        return tuple(
            materialized_case(case, values[case.id]) if case.id in values else concrete_case(case)
            for case in problem.cases
        )

    def oracle_cases(
        self, meta: ProblemMeta, oracle: str, inputs: Sequence[OracleInput]
    ) -> tuple[RunnableCase, ...]:
        """`cstudy test --stress N`: generated inputs whose expected values are the outputs of the
        oracle's Python reference, cached like generated cases."""
        cases = [Case(found.case_id, GeneratedInput(found.n, found.seed)) for found in inputs]
        source = _Source(oracle, ORACLE_CACHE_SUFFIX, ORACLE_OUTPUTS_NOTICE)
        values = self._generated(meta, cases, source)
        return tuple(materialized_case(case, values[case.id]) for case in cases)

    def _generated(
        self, meta: ProblemMeta, cases: Sequence[Case], source: "_Source"
    ) -> Mapping[str, GeneratedCase]:
        files = self._environment.files
        if files.read_text(meta.slug, GENERATOR_FILE) is None:
            raise self._error(meta, GENERATOR_FILE, "missing; generate cases need it")
        reference = solution_file(f"{source.approach}.py")
        key = files.fingerprint(meta.slug, (GENERATOR_FILE, TESTS_FILE, reference)) + source.key
        cache = self._environment.case_cache
        cached = dict(cache.load(meta.slug, key) or {})
        missing = [case for case in cases if case.id not in cached]
        if not missing:
            return cached
        self._notify(source.notice)
        cached |= self._compute(meta, source.approach, missing)
        cache.save(meta.slug, key, cached)
        return cached

    def _expected_source(self, meta: ProblemMeta) -> str:
        available = python_approaches(self._environment, meta)
        source = expected_source(meta, available)
        if source is None or source not in available:
            message = (
                f'no Python reference for "{source}" to compute generated expected values'
                if source
                else "no Python reference to compute generated expected values"
            )
            raise self._error(meta, META_FILE, message, "perf.expected_from")
        return source

    def _compute(
        self, meta: ProblemMeta, source: str, cases: Sequence[Case]
    ) -> dict[str, GeneratedCase]:
        inputs = {case.id: self._input(meta, case) for case in cases}
        runnable = [
            RunnableCase(case.id, inputs[case.id], None, hang_guard_ms=case.hang_guard_ms)
            for case in cases
        ]
        run = LanguageRun(self._environment, meta, Language.PYTHON)
        result = run.run(
            run.references([source]), [run.reference_job(source, runnable)], self._notify
        )
        reference = solution_file(f"{source}.py")
        if result.report is None:
            raise self._error(meta, reference, "does not build")
        job = result.report.job(reference_job_id(meta.slug, source))
        if job.load_error is not None:
            error = job.load_error
            raise self._error(meta, reference, f"does not load: {error.type}: {error.message}")
        outputs = {report.case_id: report.outcome for report in job.cases}
        computed: dict[str, GeneratedCase] = {}
        for case_id, run_input in inputs.items():
            outcome = outputs.get(case_id)
            if not isinstance(outcome, Returned):
                summary = outcome_summary(outcome) if outcome else "no result"
                raise self._error(meta, reference, f"failed on {case_id}: {summary}")
            computed[case_id] = GeneratedCase(run_input, Expected(outcome.output))
        return computed

    def _input(self, meta: ProblemMeta, case: Case) -> RunInput:
        generated = case.input
        assert isinstance(generated, GeneratedInput)
        generator = self._environment.content_code.generator(
            self._environment.files.path(meta.slug, GENERATOR_FILE)
        )
        document = generator.generate(generated.n, generated.seed)
        try:
            return generated_run_input(meta.kind, document)
        except ValueError as error:
            raise self._error(meta, GENERATOR_FILE, f"generate() for {case.id}: {error}") from None

    def _error(
        self, meta: ProblemMeta, name: str, message: str, location: str = ""
    ) -> ContentError:
        directory = self._environment.files.problem_directory(meta.slug)
        return ContentError([ContentIssue(f"{directory}/{name}", location, message)])
