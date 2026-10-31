"""`cstudy verify`: the content quality gate (docs/specs/authoring.md#what-cstudy-verify-checks).

Static checks first; a problem that fails them is not run. Then, per language: the generated
stub builds and loads (D1), every reference passes every case (D3; progressive references pass
every level, and their failures name the level), and with `--oracle` every approach agrees with
the oracle on small generated inputs (D4). The generator must be deterministic and its inputs
must pass `validate` (D2). Concurrent problems run D6 and D7 instead of D2 and D4
(`coding_study.application.verify_concurrency`), and project problems D1, D3 and D9 on a starter
and a reference built as folders (`coding_study.application.verify_projects`). `--oracle` and
`--ladder` need generator.py: a problem without one (practical, lld, debugging, concurrent and
project problems may omit it) skips them, reported as not applicable; the ready criteria still
require a generator for every `dsa` problem.
"""

import threading
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from coding_study.application.case_materialization import CaseMaterializer
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.language_runs import reference_job_id
from coding_study.application.ports import ProgressNotice
from coding_study.application.reference_runs import (
    ApproachResult,
    LanguageResult,
    LanguageVerifier,
    approaches_in,
    per_language,
    shown,
)
from coding_study.application.stress_judging import without_stress
from coding_study.application.verify_concurrency import ConcurrentVerifier
from coding_study.application.verify_items import (
    ItemSelection,
    ItemVerification,
    problem_slug_conflicts,
    verify_items,
)
from coding_study.application.verify_ladder import LadderResult, verify_ladder
from coding_study.application.verify_projects import SuiteCheck, verify_project
from coding_study.domain.cases import Expected, GeneratedInput, JsonValue
from coding_study.domain.comparators import Comparator
from coding_study.domain.errors import ContentError, ContentIssue, UnknownProblemError
from coding_study.domain.generated_cases import (
    generated_run_input,
    oracle_approach,
    oracle_inputs,
)
from coding_study.domain.judging import (
    CaseStatus,
    RunnableCase,
    concrete_case,
    judge,
    outcome_summary,
    verdict_summary,
)
from coding_study.domain.problem import (
    ALL_LANGUAGES,
    Language,
    Problem,
    ProblemKind,
    ProblemMeta,
    StubSource,
    Track,
)
from coding_study.domain.problem_files import (
    BROKEN_DIRECTORY,
    BUGGY_DIRECTORY,
    EXPLANATION_FILE,
    GENERATOR_FILE,
    META_FILE,
    PROBLEM_FILE,
    RUBRIC_FILE,
    SOLUTIONS_DIRECTORY,
)
from coding_study.domain.ready_criteria import MAX_SLOWEST_SHARE, has_reference, ready_problems
from coding_study.domain.runs import Returned, RunReport
from coding_study.domain.static_checks import ProblemContent, static_checks

DETERMINISM_SAMPLES = 3
"""Generator inputs checked for determinism when no --oracle inputs are requested."""


@dataclass(frozen=True, slots=True)
class VerifyRequest:
    slugs: tuple[str, ...] = ()
    """Empty: every problem."""
    track: Track | None = None
    language: Language | None = None
    """Only this language; None: every language a problem lists."""
    static_only: bool = False
    oracle_cases: int | None = None
    """`--oracle` with this many inputs; None skips the oracle cross-check."""
    require_ready: bool = False
    jobs: int | None = None
    """Languages verified at once; None: all of them."""
    ladder: bool = False
    """`--ladder`: bench the references and check their bands against `time_class`."""
    stress_runs: int | None = None
    """`--stress N`: runs per stress case and variant for D6 and D7; None: 10."""


class SkippedCheck(StrEnum):
    """A requested check that does not apply to a problem without generator.py."""

    ORACLE = "oracle"
    LADDER = "ladder"


@dataclass(frozen=True, slots=True)
class OracleResult:
    agreed: int
    """Inputs on which every approach in every language agreed with the oracle."""
    total: int
    failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProblemVerification:
    directory: str
    meta: ProblemMeta | None
    """None when the problem files did not load."""
    static_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reference_languages: tuple[Language, ...] = ()
    """Languages with at least one reference file."""
    languages: tuple[LanguageResult, ...] = ()
    """Empty when the code was not run (static failures or `--static`)."""
    oracle: OracleResult | None = None
    dynamic_errors: tuple[str, ...] = ()
    ready_errors: tuple[str, ...] = ()
    ladder: tuple[LadderResult, ...] = ()
    """With `--ladder`: one result per language whose references passed."""
    skipped: tuple[SkippedCheck, ...] = ()
    """Requested checks that need generator.py, which this problem does not have."""
    suite: SuiteCheck | None = None
    """Project problems: D9, the reference's native suite; None when it did not run."""

    @property
    def passed(self) -> bool:
        return (
            not self.static_errors
            and not self.dynamic_errors
            and not self.ready_errors
            and all(language.passed for language in self.languages)
            and (self.oracle is None or not self.oracle.failures)
            and all(result.passed for result in self.ladder)
            and (self.suite is None or self.suite.passed)
        )

    def covers(self, language: Language) -> bool:
        """At least one passing reference, or a reference file when nothing ran."""
        result = next((found for found in self.languages if found.language is language), None)
        if result is None:
            return language in self.reference_languages and not self.languages
        return result.passing > 0


@dataclass(frozen=True, slots=True)
class Coverage:
    language: Language
    covered: int
    listed: int


@dataclass(frozen=True, slots=True)
class VerifyReport:
    problems: tuple[ProblemVerification, ...]
    coverage: tuple[Coverage, ...]

    @property
    def failed(self) -> int:
        return sum(1 for problem in self.problems if not problem.passed)

    @property
    def only_static_failures(self) -> bool:
        failing = [problem for problem in self.problems if not problem.passed]
        return bool(failing) and all(problem.static_errors for problem in failing)


def verify_content(
    environment: Environment, request: VerifyRequest, notify: ProgressNotice
) -> VerifyReport:
    known = environment.files.slugs()
    item_slugs = environment.items.slugs()
    for slug in request.slugs:
        if slug not in known and slug not in item_slugs:
            raise UnknownProblemError(slug)
    selected = request.slugs or tuple(dict.fromkeys(known))
    duplicates = _duplicate_issues(environment)
    for slug, conflicts in problem_slug_conflicts(environment).items():
        duplicates[slug] = (*duplicates.get(slug, ()), *conflicts)
    all_slugs = frozenset((*known, *item_slugs))
    verifier = _ProblemVerifier(environment, request, notify, all_slugs)
    checked = (
        verifier.verify(slug, duplicates.get(slug, ())) for slug in selected if slug in known
    )
    problems = tuple(problem for problem in checked if problem is not None)
    items = verify_items(environment, _item_selection(request), all_slugs)
    return VerifyReport(
        (*problems, *map(_as_verification, items)), _coverage(problems, request.language)
    )


def _item_selection(request: VerifyRequest) -> ItemSelection:
    return ItemSelection(request.slugs, request.track, request.require_ready)


def _as_verification(item: ItemVerification) -> ProblemVerification:
    """Items run no code, so they have no meta, languages or coverage."""
    return ProblemVerification(
        directory=item.directory,
        meta=None,
        static_errors=item.static_errors,
        warnings=item.warnings,
        ready_errors=item.ready_errors,
    )


def problem_content(environment: Environment, slug: str, problem: Problem) -> ProblemContent:
    files = environment.files
    return ProblemContent(
        directory=files.problem_directory(slug),
        problem=problem,
        problem_markdown=files.read_text(slug, PROBLEM_FILE),
        explanation=files.read_text(slug, EXPLANATION_FILE),
        files=files.file_names(slug),
        solution_files=files.file_names(slug, SOLUTIONS_DIRECTORY),
        buggy_files=files.file_names(slug, BUGGY_DIRECTORY),
        rubric=files.read_text(slug, RUBRIC_FILE),
        broken_files=files.file_names(slug, BROKEN_DIRECTORY),
    )


def _duplicate_issues(environment: Environment) -> dict[str, tuple[str, ...]]:
    """S2: ids and slugs are unique across the problems directory."""
    files = environment.files
    names = files.directory_names()
    directories = [f"{files.directory}/{name}" for name in names]
    keys = [(name.partition("-")[0], name.partition("-")[2]) for name in names]
    issues: dict[str, list[str]] = {}
    for position, (problem_id, slug) in enumerate(keys):
        for other, (other_id, other_slug) in zip(directories, keys, strict=True):
            if other == directories[position]:
                continue
            if other_id == problem_id:
                issues.setdefault(slug, []).append(
                    f'{directories[position]}: id "{problem_id}" is also used by {other}'
                )
            if other_slug == slug:
                issues.setdefault(slug, []).append(
                    f'{directories[position]}: slug "{slug}" is also used by {other}'
                )
    return {slug: tuple(dict.fromkeys(found)) for slug, found in issues.items()}


def _coverage(
    problems: Sequence[ProblemVerification], only: Language | None
) -> tuple[Coverage, ...]:
    loaded = [(problem, problem.meta) for problem in problems if problem.meta is not None]
    languages = (only,) if only else ALL_LANGUAGES
    return tuple(
        Coverage(
            language,
            covered=sum(1 for problem, _ in loaded if problem.covers(language)),
            listed=sum(1 for _, meta in loaded if language in meta.languages),
        )
        for language in languages
    )


class _ProblemVerifier:
    def __init__(
        self,
        environment: Environment,
        request: VerifyRequest,
        notify: ProgressNotice,
        known_slugs: frozenset[str],
    ) -> None:
        self._environment = environment
        self._request = request
        self._notify = notify
        self._known_slugs = known_slugs

    def verify(self, slug: str, duplicates: tuple[str, ...]) -> ProblemVerification | None:
        """None when the problem is outside `--track`, or a project outside `--lang`: a project
        problem counts only in its one language."""
        directory = self._environment.files.problem_directory(slug)
        try:
            problem = self._environment.problems.load(slug)
        except ContentError as error:
            issues = (*duplicates, *(str(issue) for issue in error.issues))
            return ProblemVerification(directory, None, static_errors=issues)
        if self._request.track not in (None, problem.meta.track):
            return None
        if problem.meta.kind is ProblemKind.PROJECT and self._request.language not in (
            None,
            *problem.meta.languages,
        ):
            return None
        content = problem_content(self._environment, slug, problem)
        static = static_checks(content)
        verification = ProblemVerification(
            directory=directory,
            meta=problem.meta,
            static_errors=(*duplicates, *(str(issue) for issue in static.errors)),
            warnings=tuple(str(issue) for issue in (*static.warnings, *self._related(content))),
            reference_languages=_reference_languages(content),
            ready_errors=ready_problems(content) if self._request.require_ready else (),
        )
        if verification.static_errors or self._request.static_only:
            return verification
        return _DynamicChecks(self._environment, self._request, self._notify, problem).apply(
            verification
        )

    def _related(self, content: ProblemContent) -> list[ContentIssue]:
        return [
            ContentIssue(
                f"{content.directory}/{META_FILE}", "related", f'"{slug}" is not a problem (yet)'
            )
            for slug in content.problem.meta.related
            if slug not in self._known_slugs
        ]


def _deadline_margin_problems(results: Sequence[LanguageResult]) -> tuple[str, ...]:
    """Ready: the slowest correct stress run uses at most 25% of its deadline."""
    shares = [
        (share, result.language, check)
        for result in results
        for check in result.stress
        if not check.is_broken and (share := check.verdict.slowest_share) is not None
    ]
    if not shares:
        return ()
    share, language, check = max(shares, key=lambda item: item[0])
    if share <= MAX_SLOWEST_SHARE:
        return ()
    where = f"{language} {check.target_id} {check.verdict.case_id} {check.verdict.variant}"
    return (
        f"the slowest correct stress run ({where}) uses {share:.0%} of its deadline; "
        f"at most {MAX_SLOWEST_SHARE:.0%}",
    )


def _reference_languages(content: ProblemContent) -> tuple[Language, ...]:
    approaches = content.problem.meta.approaches
    return tuple(
        language
        for language in Language
        if any(has_reference(content, approach.id, language) for approach in approaches)
    )


class _DynamicChecks:
    def __init__(
        self,
        environment: Environment,
        request: VerifyRequest,
        notify: ProgressNotice,
        problem: Problem,
    ) -> None:
        self._environment = environment
        self._request = request
        self._notify = notify
        self._problem = problem
        self._meta = problem.meta
        self._errors: list[str] = []
        self._runner_slot = threading.Lock()
        """Concurrent problems: one language's runner runs its stress cases at a time."""

    def apply(self, verification: ProblemVerification) -> ProblemVerification:
        generated = self._environment.files.read_text(self._meta.slug, GENERATOR_FILE) is not None
        cases = self._cases()
        oracle_cases = self._generator_checks() if generated else ()
        try:
            comparator = problem_comparator(self._environment, self._meta)
        except ContentError as error:
            errors = (*self._errors, *(str(issue) for issue in error.issues))
            return replace(verification, dynamic_errors=errors)
        languages = [
            language
            for language in self._meta.languages
            if self._request.language in (None, language)
        ]
        if self._meta.kind is ProblemKind.PROJECT:
            return self._project(verification, languages)
        runs = per_language(
            languages,
            lambda language: self._language(language, cases, oracle_cases, comparator),
            self._request.jobs,
        )
        oracle = (
            self._oracle(runs, oracle_cases, comparator)
            if generated and self._request.oracle_cases is not None
            else None
        )
        results = tuple(result for result, _ in runs.values())
        ladder = self._ladder(results) if generated and self._request.ladder else ()
        margin_errors = _deadline_margin_problems(results) if self._request.require_ready else ()
        return replace(
            verification,
            languages=results,
            oracle=oracle,
            dynamic_errors=tuple(self._errors),
            ladder=ladder,
            ready_errors=verification.ready_errors + margin_errors,
            warnings=verification.warnings + self._busy_machine_notes(results, margin_errors),
            skipped=() if generated else self._generator_checks_requested(),
        )

    def _project(
        self, verification: ProblemVerification, languages: Sequence[Language]
    ) -> ProblemVerification:
        """D1, D3 and D9 in the project's one language; D2, D4 and D5 do not apply."""
        projects = [
            verify_project(self._environment, self._problem, language, self._notify)
            for language in languages
        ]
        return replace(
            verification,
            languages=tuple(project.language for project in projects),
            suite=next((project.suite for project in projects), None),
            dynamic_errors=tuple(self._errors),
            skipped=self._generator_checks_requested(),
        )

    def _busy_machine_notes(
        self, results: Sequence[LanguageResult], margin_errors: Sequence[str]
    ) -> tuple[str, ...]:
        """Failed stress checks name a busy machine: with other work on the cores, races show
        less often and runs take longer. The thresholds stay; the note tells a load flake from
        a weak stress case."""
        failed = any(not check.ok for result in results for check in result.stress)
        if not (failed or margin_errors):
            return ()
        return tuple(
            f"stress checks failed on a busy machine ({condition}): races show less often and "
            "runs take longer; verify again when it is idle"
            for condition in self._environment.machine.snapshot().warnings
        )

    def _generator_checks_requested(self) -> tuple[SkippedCheck, ...]:
        requested = {
            SkippedCheck.ORACLE: self._request.oracle_cases is not None,
            SkippedCheck.LADDER: self._request.ladder,
        }
        return tuple(check for check, wanted in requested.items() if wanted)

    def _ladder(self, results: Sequence[LanguageResult]) -> tuple[LadderResult, ...]:
        """D5, one language at a time so benches never share the machine; only languages whose
        references passed their cases."""
        return tuple(
            verify_ladder(self._environment, self._problem, result.language, self._notify)
            for result in results
            if result.approaches and result.passed
        )

    def _cases(self) -> tuple[RunnableCase, ...]:
        """Generated cases materialized; a concurrent problem's stress cases are planned later."""
        sequential = without_stress(self._problem)
        try:
            return CaseMaterializer(self._environment, self._notify).runnable_cases(sequential)
        except ContentError as error:
            self._errors += [str(issue) for issue in error.issues]
            return tuple(
                concrete_case(case)
                for case in sequential.cases
                if not isinstance(case.input, GeneratedInput)
            )

    def _generator_checks(self) -> tuple[RunnableCase, ...]:
        """D2 on the generate cases and the oracle inputs; returns the oracle cases."""
        try:
            return self._generated_inputs()
        except ContentError as error:
            self._errors += [str(issue) for issue in error.issues]
            return ()

    def _generated_inputs(self) -> tuple[RunnableCase, ...]:
        files = self._environment.files
        generator = self._environment.content_code.generator(
            files.path(self._meta.slug, GENERATOR_FILE)
        )
        source = f"{files.problem_directory(self._meta.slug)}/{GENERATOR_FILE}"
        samples = [
            (case.id, case.input.n, case.input.seed)
            for case in self._problem.cases
            if isinstance(case.input, GeneratedInput)
        ]
        count = self._request.oracle_cases or DETERMINISM_SAMPLES
        oracles = oracle_inputs(count)
        samples += [(oracle.case_id, oracle.n, oracle.seed) for oracle in oracles]
        inputs: dict[str, dict[str, JsonValue]] = {}
        for case_id, n, seed in samples:
            first, second = generator.generate(n, seed), generator.generate(n, seed)
            call = f"generate(n={n}, seed={seed})"
            if first != second:
                self._errors.append(f"{source}: {call} is not deterministic")
            rejected = generator.validate(first)
            if rejected is not None:
                self._errors.append(f"{source}: validate rejected {call}: {rejected}")
            inputs[case_id] = first
        if self._request.oracle_cases is None:
            return ()
        try:
            return tuple(
                RunnableCase(
                    oracle.case_id,
                    generated_run_input(self._meta.kind, inputs[oracle.case_id]),
                    None,
                )
                for oracle in oracles
            )
        except ValueError as error:
            self._errors.append(f"{source}: {error}")
            return ()

    def _language(
        self,
        language: Language,
        cases: Sequence[RunnableCase],
        oracle_cases: Sequence[RunnableCase],
        comparator: Comparator,
    ) -> tuple[LanguageResult, RunReport | None]:
        verifier = LanguageVerifier(self._environment, self._meta, language, self._notify)
        sample = next((case for case in cases if not case.generated), None)
        stub = (
            verifier.buggy_problem(cases, comparator)
            if self._meta.stub is StubSource.BUGGY
            else verifier.stub_problem(sample)
        )
        problems = [stub] if stub else []
        approaches = approaches_in(self._environment, self._meta, language)
        if not approaches:
            return LanguageResult(language, (), tuple(problems)), None
        if self._meta.concurrency is not None:
            concurrent = ConcurrentVerifier(
                self._environment, self._problem, language, self._notify, self._runner_slot
            ).verify(approaches, cases, comparator, self._request.stress_runs)
            result = LanguageResult(
                language,
                concurrent.approaches,
                (*problems, *concurrent.problems),
                concurrent.broken,
                concurrent.stress,
            )
            return result, None
        code_run = verifier.references(approaches, [*cases, *oracle_cases])
        if code_run.report is None:
            diagnostics = code_run.build_failure.diagnostics if code_run.build_failure else ()
            problems.append("references do not build: " + " | ".join(diagnostics[:3]))
            failed = tuple(ApproachResult(approach, ("not built",)) for approach in approaches)
            return LanguageResult(language, failed, tuple(problems)), None
        results = tuple(
            self._approach(approach, code_run.report, cases, comparator) for approach in approaches
        )
        return LanguageResult(language, results, tuple(problems)), code_run.report

    def _approach(
        self,
        approach: str,
        report: RunReport,
        cases: Sequence[RunnableCase],
        comparator: Comparator,
    ) -> ApproachResult:
        job = report.job(reference_job_id(self._meta.slug, approach))
        if job.load_error is not None:
            error = job.load_error
            return ApproachResult(approach, (f"does not load: {error.type}: {error.message}",))
        judgement = judge(cases, job, comparator)
        failures = [
            self._level_prefix(verdict.case.id) + verdict_summary(verdict)
            for verdict in judgement.verdicts
            if verdict.status is not CaseStatus.PASS
        ]
        return ApproachResult(approach, shown(failures))

    def _level_prefix(self, case_id: str) -> str:
        """`level <n> ` for a case of a progressive problem, else nothing."""
        level = next((case.level for case in self._problem.cases if case.id == case_id), None)
        return f"level {level} " if level is not None else ""

    def _oracle(
        self,
        runs: dict[Language, tuple[LanguageResult, RunReport | None]],
        oracle_cases: Sequence[RunnableCase],
        comparator: Comparator,
    ) -> OracleResult:
        oracle = oracle_approach(self._meta)
        python = runs.get(Language.PYTHON, (None, None))[1]
        if oracle is None or python is None or not oracle_cases:
            reason = "--oracle needs an oracle approach with a Python reference and generator.py"
            return OracleResult(0, len(oracle_cases), (reason,))
        failures: list[str] = []
        outputs = self._oracle_outputs(python, oracle, oracle_cases, failures)
        expected = tuple(
            RunnableCase(case.id, case.input, Expected(outputs[case.id]))
            for case in oracle_cases
            if case.id in outputs
        )
        agreed = set(outputs)
        for language, (_, report) in runs.items():
            if report is None:
                continue
            for approach in approaches_in(self._environment, self._meta, language):
                if (language, approach) == (Language.PYTHON, oracle):
                    continue
                job = report.job(reference_job_id(self._meta.slug, approach))
                if job.load_error is not None:
                    agreed.clear()
                    continue
                for verdict in judge(expected, job, comparator).verdicts:
                    if verdict.status is not CaseStatus.PASS:
                        agreed.discard(verdict.case.id)
                        failures.append(f"{language} {approach} {verdict_summary(verdict)}")
        return OracleResult(len(agreed), len(oracle_cases), shown(failures))

    def _oracle_outputs(
        self,
        report: RunReport,
        oracle: str,
        oracle_cases: Sequence[RunnableCase],
        failures: list[str],
    ) -> dict[str, JsonValue]:
        job = report.job(reference_job_id(self._meta.slug, oracle))
        outcomes = {case.case_id: case.outcome for case in job.cases}
        outputs: dict[str, JsonValue] = {}
        for case in oracle_cases:
            outcome = outcomes.get(case.id)
            if isinstance(outcome, Returned):
                outputs[case.id] = outcome.output
            else:
                summary = outcome_summary(outcome) if outcome else "no result"
                failures.append(f"oracle {oracle} failed on {case.id}: {summary}")
        return outputs
