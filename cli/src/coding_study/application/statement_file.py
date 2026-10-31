""".statements/<slug>.md in the workspace, rendered from problem.md
(docs/specs/cli.md#cstudy-start).

`cstudy start` writes it; `cstudy test` writes it again when a progressive problem unlocks a level,
and `cstudy submit` when a project problem opens one. A project problem's statement speaks its
language (docs/specs/problem-format.md#statement).
"""

from coding_study.application.environment import Environment
from coding_study.domain import layout
from coding_study.domain.problem import Problem, ProblemKind
from coding_study.domain.problem_files import PROBLEM_FILE
from coding_study.domain.project import render_project_statement
from coding_study.domain.statement import render_statement


def statement_text(environment: Environment, problem: Problem, unlocked_level: int | None) -> str:
    """The statement with levels 1 to `unlocked_level` of a progressive or project problem."""
    markdown = environment.files.read_text(problem.meta.slug, PROBLEM_FILE)
    if problem.meta.kind is ProblemKind.PROJECT:
        return render_project_statement(problem, markdown, unlocked_level)
    return render_statement(problem, markdown, unlocked_level)


def write_statement(environment: Environment, problem: Problem, unlocked_level: int | None) -> str:
    """Writes the statement file; returns its path."""
    path = layout.statement_path(problem.meta.slug)
    environment.workspace.write_text(path, statement_text(environment, problem, unlocked_level))
    return path
