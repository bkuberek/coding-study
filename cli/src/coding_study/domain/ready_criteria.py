"""What `status: ready` requires (docs/specs/authoring.md#ready-criteria).

`cstudy verify --require-ready` enforces these on top of the static and dynamic checks.
"""

from coding_study.domain.cases import GeneratedInput
from coding_study.domain.concurrency import Concurrency
from coding_study.domain.layout import SOURCE_EXTENSIONS, reference_file_name
from coding_study.domain.problem import (
    ApproachRole,
    ContentStatus,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.problem_files import GENERATOR_FILE
from coding_study.domain.static_checks import ProblemContent
from coding_study.domain.stress import StressScenario

MIN_DSA_APPROACHES = 2
MIN_VISIBLE_CASES = 2
MIN_HIDDEN_CASES = 8
MIN_LEVELS = 2
MIN_VISIBLE_CASES_PER_LEVEL = 1
MIN_HIDDEN_CASES_PER_LEVEL = 2
MIN_CONCURRENT_HIDDEN_CASES = 4
MIN_STRESS_CASES = 2
MAX_SLOWEST_SHARE = 0.25
"""Concurrent problems: the slowest correct run uses at most this share of its deadline."""


def ready_problems(content: ProblemContent) -> tuple[str, ...]:
    """Every reason the problem is not ready; empty when it is."""
    meta = content.problem.meta
    problems: list[str] = []
    if meta.status is not ContentStatus.READY:
        problems.append(f"status is {meta.status}, not ready")
    missing = [language for language in meta.languages if not _has_optimal(content, language)]
    if missing:
        problems.append(f"no optimal reference in {', '.join(missing)}")
    problems += _missing_references(content)
    if meta.track is Track.DSA:
        problems += _dsa_problems(content)
    if meta.kind is ProblemKind.PROGRESSIVE:
        problems += _level_problems(content)
    if meta.concurrency is not None:
        problems += _concurrent_problems(content, meta.concurrency)
    else:
        problems += _case_problems(content)
    return tuple(problems)


def _has_optimal(content: ProblemContent, language: Language) -> bool:
    extension = SOURCE_EXTENSIONS[language]
    return any(
        f"{approach.id}.{extension}" in content.solution_files
        for approach in content.problem.meta.approaches
        if approach.role is ApproachRole.OPTIMAL
    )


def _missing_references(content: ProblemContent) -> list[str]:
    """Every approach has a reference in each of its languages: the problem's, unless the
    approach names fewer."""
    languages = content.problem.meta.languages
    problems: list[str] = []
    for approach in content.problem.meta.approaches:
        missing = [
            language
            for language in languages
            if approach.covers(language, languages)
            and reference_file_name(approach.id, language) not in content.solution_files
        ]
        if missing:
            problems.append(f"{approach.id} has no reference in {', '.join(missing)}")
    return problems


def _dsa_problems(content: ProblemContent) -> list[str]:
    meta = content.problem.meta
    problems: list[str] = []
    if len(meta.approaches) < MIN_DSA_APPROACHES:
        problems.append(f"dsa problems need at least {MIN_DSA_APPROACHES} approaches")
    python = f".{SOURCE_EXTENSIONS[Language.PYTHON]}"
    if not any(
        approach.oracle and f"{approach.id}{python}" in content.solution_files
        for approach in meta.approaches
    ):
        problems.append("dsa problems need an oracle approach in Python")
    if GENERATOR_FILE not in content.files:
        problems.append(f"dsa problems need {GENERATOR_FILE}")
    return problems


def _case_problems(content: ProblemContent) -> list[str]:
    cases = content.problem.cases
    visible = sum(1 for case in cases if case.visible)
    generated = [case.input for case in cases if isinstance(case.input, GeneratedInput)]
    hidden = len(cases) - visible - len(generated)
    problems: list[str] = []
    if visible < MIN_VISIBLE_CASES:
        problems.append(f"needs at least {MIN_VISIBLE_CASES} visible cases (has {visible})")
    if hidden < MIN_HIDDEN_CASES:
        problems.append(
            f"needs at least {MIN_HIDDEN_CASES} hidden hand-written cases (has {hidden})"
        )
    largest = _largest_size(content.problem.meta)
    needs_generated = content.problem.meta.track is Track.DSA or GENERATOR_FILE in content.files
    if needs_generated and not any(generated_input.n == largest for generated_input in generated):
        problems.append(f"needs a generate case at the largest ladder size (n={largest})")
    return problems


def _concurrent_problems(content: ProblemContent, concurrency: Concurrency) -> list[str]:
    """Sequential cases, stress cases and a broken reference per language; D7 and the deadline
    margin are dynamic and checked by `cstudy verify`."""
    cases = content.problem.cases
    stress = [case for case in cases if isinstance(case.input, StressScenario)]
    sequential = [case for case in cases if not isinstance(case.input, StressScenario)]
    visible = sum(1 for case in sequential if case.visible)
    hidden = len(sequential) - visible
    problems: list[str] = []
    if visible < MIN_VISIBLE_CASES:
        problems.append(f"needs at least {MIN_VISIBLE_CASES} visible cases (has {visible})")
    if hidden < MIN_CONCURRENT_HIDDEN_CASES:
        problems.append(
            f"needs at least {MIN_CONCURRENT_HIDDEN_CASES} hidden sequential cases (has {hidden})"
        )
    if len(stress) < MIN_STRESS_CASES:
        problems.append(f"needs at least {MIN_STRESS_CASES} stress cases (has {len(stress)})")
    languages = content.problem.meta.languages
    uncovered = [
        language
        for language in languages
        if not any(broken.covers(language, languages) for broken in concurrency.broken)
    ]
    if uncovered:
        problems.append(f"no broken reference in {', '.join(uncovered)}")
    return problems


def _level_problems(content: ProblemContent) -> list[str]:
    """Progressive problems: enough levels, and visible and hidden cases in each."""
    levels = content.problem.meta.levels
    problems: list[str] = []
    if len(levels) < MIN_LEVELS:
        problems.append(f"progressive problems need at least {MIN_LEVELS} levels")
    for level in levels:
        cases = [case for case in content.problem.cases if case.level == level.number]
        visible = sum(1 for case in cases if case.visible)
        hidden = sum(
            1 for case in cases if not case.visible and not isinstance(case.input, GeneratedInput)
        )
        if visible < MIN_VISIBLE_CASES_PER_LEVEL:
            problems.append(
                f"level {level.number} needs at least {MIN_VISIBLE_CASES_PER_LEVEL} visible case "
                f"(has {visible})"
            )
        if hidden < MIN_HIDDEN_CASES_PER_LEVEL:
            problems.append(
                f"level {level.number} needs at least {MIN_HIDDEN_CASES_PER_LEVEL} hidden "
                f"hand-written cases (has {hidden})"
            )
    return problems


def _largest_size(meta: ProblemMeta) -> int:
    return max(meta.perf.size_ladder)
