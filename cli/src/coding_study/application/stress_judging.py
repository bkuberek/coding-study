"""What judging a concurrent problem's stress runs needs (docs/specs/problem-format.md#invariants):
the `ops` comparator for `final.expected`, and stress_checker.py when the problem has one.
"""

from collections.abc import Sequence
from dataclasses import replace

from coding_study.application.environment import Environment
from coding_study.domain.cases import Case
from coding_study.domain.comparators import Comparator
from coding_study.domain.problem import Problem
from coding_study.domain.problem_files import STRESS_CHECKER_FILE
from coding_study.domain.stress import StressScenario
from coding_study.domain.stress_verdict import StressJudging


def stress_judging(
    environment: Environment, problem: Problem, comparator: Comparator
) -> StressJudging:
    """Loads stress_checker.py only when a file exists; raises ContentError when it is broken."""
    files = environment.files
    slug = problem.meta.slug
    if files.read_text(slug, STRESS_CHECKER_FILE) is None:
        return StressJudging(comparator)
    checker = environment.content_code.stress_checker(files.path(slug, STRESS_CHECKER_FILE))
    return StressJudging(comparator, checker)


def without_stress(problem: Problem) -> Problem:
    """The problem with its sequential cases only."""
    return replace(problem, cases=sequential_cases(problem))


def sequential_cases(problem: Problem) -> tuple[Case, ...]:
    return tuple(case for case in problem.cases if not isinstance(case.input, StressScenario))


def stress_case_ids(problem: Problem) -> Sequence[str]:
    return [case.id for case in problem.cases if isinstance(case.input, StressScenario)]
