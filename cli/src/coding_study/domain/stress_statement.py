"""The stress-case table that rendered statements append to `## Concurrency`.

Spec: docs/specs/authoring.md#problemmd. The user sees what each stress case checks: its note,
the worker groups with their counts and iterations, and the invariant types.
"""

from coding_study.domain.problem import Problem
from coding_study.domain.stress import Repeat, StressScenario, WorkerGroup, invariant_type

CONCURRENCY_SECTION = "Concurrency"
TIMES = "\N{MULTIPLICATION SIGN}"
FINAL_VALUES = "final values"
"""Shown when `final.expected` is checked."""
HEADER = ("| Stress case | Note | Workers | Checks |", "|-------------|------|---------|--------|")


def stress_table(problem: Problem) -> tuple[str, ...]:
    """The table's lines; empty when the problem has no stress cases."""
    rows = tuple(
        _row(case.id, case.note, case.input)
        for case in problem.cases
        if isinstance(case.input, StressScenario)
    )
    return (*HEADER, *rows) if rows else ()


def _row(case_id: str, note: str | None, scenario: StressScenario) -> str:
    workers = ", ".join(_group(group) for group in scenario.workers)
    checks = ", ".join(_check_names(scenario))
    return f"| {case_id} | {note or ''} | {workers} | {checks} |"


def _group(group: WorkerGroup) -> str:
    return f"{group.group} {group.count} {TIMES} {_repeat(group.repeat)}"


def _repeat(repeat: Repeat) -> str:
    overrides = ", ".join(f"{language} {count}" for language, count in repeat.per_language.items())
    return f"{repeat.default} ({overrides})" if overrides else str(repeat.default)


def _check_names(scenario: StressScenario) -> list[str]:
    names = [invariant_type(invariant) for invariant in scenario.invariants]
    final = scenario.final
    if final is not None and final.expected is not None:
        names.append(FINAL_VALUES)
    return names
