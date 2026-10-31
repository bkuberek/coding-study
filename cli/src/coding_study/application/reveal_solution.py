"""`cstudy solution`: reference code with its explanation (docs/specs/cli.md#cstudy-solution).

Problems with a rubric.md (low-level design) also show it: the design criteria for self-review
and the reference design. Concurrent problems can show a deliberately broken reference instead,
as a "spot the bug" exercise. Revealing the solution of an attempt that has not passed yet grades
it `again` (docs/specs/progress-and-scheduling.md#grade).
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.mock_interview import require_no_running_mock
from coding_study.application.project_start import project_start_language
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt
from coding_study.domain.concurrency import BrokenReference
from coding_study.domain.errors import UsageError
from coding_study.domain.explanation import Explanation
from coding_study.domain.precedence import first_set
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    Language,
    Problem,
    ProblemKind,
    ProblemMeta,
)
from coding_study.domain.problem_files import (
    BROKEN_DIRECTORY,
    EXPLANATION_FILE,
    RUBRIC_FILE,
    SOLUTIONS_DIRECTORY,
    broken_file,
    solution_file,
)
from coding_study.domain.project_reference import ReferenceFile, reference_files


@dataclass(frozen=True, slots=True)
class SolutionRequest:
    slug: str
    language: Language | None = None
    """None: the language of the attempt in progress, else the config's `default_lang`."""
    approach_id: str | None = None
    """None: the first `optimal` approach."""
    all_approaches: bool = False
    explanation_only: bool = False
    broken: str | None = None
    """`--broken [ID]`: "" for the first broken reference with a file in the language."""


@dataclass(frozen=True, slots=True)
class BrokenSolution:
    broken: BrokenReference
    explanation: str | None
    """The `## Broken: <id>` section of explanation.md, heading included."""
    code: str | None
    available: tuple[Language, ...]


@dataclass(frozen=True, slots=True)
class ApproachSolution:
    approach: Approach
    explanation: str | None
    """The approach's section of explanation.md, heading included."""
    code: str | None
    """None when there is no reference in the language, or with `explanation_only`."""
    available: tuple[Language, ...]
    """Languages with a reference file for this approach."""


@dataclass(frozen=True, slots=True)
class SolutionView:
    meta: ProblemMeta
    language: Language
    overview: str | None
    approaches: tuple[ApproachSolution, ...]
    rubric: str | None = None
    """rubric.md as written: design criteria, then the reference design."""
    broken: BrokenSolution | None = None
    """With `--broken`: the broken reference shown instead of the approaches."""
    project_files: tuple[ReferenceFile, ...] = ()
    """A project problem: its reference as files added in full and diffs against the starter."""


def show_solution(environment: Environment, request: SolutionRequest) -> SolutionView:
    """Raises UsageError during a mock interview."""
    require_no_running_mock(environment, "cstudy solution")
    problem = environment.problems.load(request.slug)
    meta = problem.meta
    if meta.kind is ProblemKind.PROJECT:
        return _project_solution(environment, problem, request)
    attempt = environment.progress.active_attempt(request.slug)
    language = first_set(
        request.language,
        attempt.language if attempt else None,
        default=environment.config.default_lang,
    )
    text = environment.files.read_text(meta.slug, EXPLANATION_FILE)
    explanation = Explanation(text) if text is not None else None
    overview = explanation.overview if explanation else None
    parts = _Parts(environment, meta, explanation)
    if request.broken is not None:
        broken = _selected_broken(environment, meta, request, language)
        return SolutionView(
            meta, language, None, (), broken=parts.broken(broken, request, language)
        )
    return SolutionView(
        meta=meta,
        language=language,
        overview=overview.text if overview else None,
        approaches=tuple(
            parts.solution(approach, None if request.explanation_only else language)
            for approach in _selected(meta, request)
        ),
        rubric=environment.files.read_text(meta.slug, RUBRIC_FILE),
    )


def _project_solution(
    environment: Environment, problem: Problem, request: SolutionRequest
) -> SolutionView:
    """A project's one approach with `### Design`, then its overlay on the starter, in its one
    language (docs/specs/cli.md#cstudy-solution)."""
    meta = problem.meta
    if request.broken is not None:
        raise UsageError(f"{meta.slug} has no broken references (concurrent problems only)")
    language = project_start_language(problem, request.language)
    text = environment.files.read_text(meta.slug, EXPLANATION_FILE)
    explanation = Explanation(text) if text is not None else None
    overview = explanation.overview if explanation else None
    parts = _Parts(environment, meta, explanation)
    approaches = tuple(
        ApproachSolution(approach, parts.section(approach.id), None, (language,))
        for approach in _selected(meta, request)
    )
    return SolutionView(
        meta=meta,
        language=language,
        overview=overview.text if overview else None,
        approaches=approaches,
        project_files=() if request.explanation_only else _overlay_files(problem, approaches),
    )


def _overlay_files(
    problem: Problem, approaches: tuple[ApproachSolution, ...]
) -> tuple[ReferenceFile, ...]:
    files = problem.project_files
    if files is None:
        return ()
    overlays = (files.overlays.get(part.approach.id) for part in approaches)
    return tuple(
        found
        for overlay in overlays
        if overlay is not None
        for found in reference_files(files.starter, overlay)
    )


def attempt_to_mark(environment: Environment, slug: str) -> Attempt | None:
    """The attempt in progress that revealing the solution would grade `again`, if any."""
    attempt = environment.progress.active_attempt(slug)
    if attempt is None or attempt.first_pass_at is not None or attempt.solution_revealed:
        return None
    return attempt


def mark_revealed(environment: Environment, attempt: Attempt) -> None:
    environment.progress.update_attempt(replace(attempt, solution_revealed=True))


def _selected_broken(
    environment: Environment, meta: ProblemMeta, request: SolutionRequest, language: Language
) -> BrokenReference:
    if request.approach_id is not None or request.all_approaches:
        raise UsageError("--broken shows one broken reference; drop --approach and --all")
    concurrency = meta.concurrency
    if concurrency is None or not concurrency.broken:
        raise UsageError(f"{meta.slug} has no broken references (concurrent problems only)")
    if request.broken:
        chosen = concurrency.broken_reference(request.broken)
        if chosen is None:
            known = ", ".join(broken.id for broken in concurrency.broken)
            raise UsageError(f'no broken reference "{request.broken}" in {meta.slug}; {known}')
        return chosen
    files = set(environment.files.file_names(meta.slug, BROKEN_DIRECTORY))
    with_file = (
        broken
        for broken in concurrency.broken
        if layout.reference_file_name(broken.id, language) in files
    )
    return next(with_file, concurrency.broken[0])


def _selected(meta: ProblemMeta, request: SolutionRequest) -> tuple[Approach, ...]:
    if request.all_approaches:
        return meta.approaches
    if request.approach_id is None:
        optimal = (
            approach for approach in meta.approaches if approach.role is ApproachRole.OPTIMAL
        )
        return (next(optimal, meta.approaches[0]),)
    chosen = next(
        (approach for approach in meta.approaches if approach.id == request.approach_id), None
    )
    if chosen is None:
        known = ", ".join(approach.id for approach in meta.approaches)
        raise UsageError(f'no approach "{request.approach_id}" in {meta.slug}; approaches: {known}')
    return (chosen,)


class _Parts:
    def __init__(
        self, environment: Environment, meta: ProblemMeta, explanation: Explanation | None
    ) -> None:
        self._environment = environment
        self._meta = meta
        self._explanation = explanation
        self._files = set(environment.files.file_names(meta.slug, SOLUTIONS_DIRECTORY))

    def solution(self, approach: Approach, language: Language | None) -> ApproachSolution:
        available = tuple(
            known
            for known in Language
            if layout.reference_file_name(approach.id, known) in self._files
        )
        code = None
        if language is not None and language in available:
            name = solution_file(layout.reference_file_name(approach.id, language))
            code = self._environment.files.read_text(self._meta.slug, name)
        return ApproachSolution(approach, self.section(approach.id), code, available)

    def broken(
        self, broken: BrokenReference, request: SolutionRequest, language: Language
    ) -> BrokenSolution:
        files = set(self._environment.files.file_names(self._meta.slug, BROKEN_DIRECTORY))
        available = tuple(
            known for known in Language if layout.reference_file_name(broken.id, known) in files
        )
        code = None
        if not request.explanation_only and language in available:
            name = broken_file(layout.reference_file_name(broken.id, language))
            code = self._environment.files.read_text(self._meta.slug, name)
        return BrokenSolution(broken, self._broken_section(broken.id), code, available)

    def section(self, approach_id: str) -> str | None:
        """The approach's section of explanation.md, heading included."""
        if self._explanation is None:
            return None
        found = self._explanation.approach(approach_id)
        return self._explanation.section_text(found.section) if found else None

    def _broken_section(self, broken_id: str) -> str | None:
        if self._explanation is None:
            return None
        found = next(
            (item for item in self._explanation.broken() if item.broken_id == broken_id), None
        )
        return self._explanation.section_text(found.section) if found else None
