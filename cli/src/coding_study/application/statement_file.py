""".statements/<slug>.md in the workspace, rendered from problem.md
(docs/specs/cli.md#cstudy-start).

`cstudy start` writes it; `cstudy test` writes it again when a progressive problem unlocks a level,
and `cstudy submit` when a project problem opens one. A project problem's statement speaks its
language (docs/specs/problem-format.md#statement). While an attempt is in progress, a problem with
levels shows the level to try under its title (progress-and-scheduling.md#level-passes).
"""

from coding_study.application.environment import Environment
from coding_study.application.level_passes import language_mastery
from coding_study.domain import layout
from coding_study.domain.problem import Problem, ProblemKind
from coding_study.domain.problem_files import PROBLEM_FILE
from coding_study.domain.project import render_project_statement
from coding_study.domain.statement import render_statement, with_goal


def statement_text(environment: Environment, problem: Problem, unlocked_level: int | None) -> str:
    """The statement with levels 1 to `unlocked_level` of a progressive or project problem."""
    markdown = environment.files.read_text(problem.meta.slug, PROBLEM_FILE)
    if problem.meta.kind is ProblemKind.PROJECT:
        rendered = render_project_statement(problem, markdown, unlocked_level)
    else:
        rendered = render_statement(problem, markdown, unlocked_level)
    goal = _goal(environment, problem)
    return rendered if goal is None else with_goal(rendered, goal)


def _goal(environment: Environment, problem: Problem) -> str | None:
    """`last time: through level 2 of 4; try level 3`, from the earlier attempts in the language
    of the attempt in progress; None without one, or without a level to try."""
    attempt = environment.progress.active_attempt(problem.meta.slug)
    if attempt is None:
        return None
    mastery = language_mastery(environment, attempt, problem)
    return mastery.goal if mastery else None


def write_statement(environment: Environment, problem: Problem, unlocked_level: int | None) -> str:
    """Writes the statement file; returns its path."""
    path = layout.statement_path(problem.meta.slug)
    environment.workspace.write_text(path, statement_text(environment, problem, unlocked_level))
    return path
