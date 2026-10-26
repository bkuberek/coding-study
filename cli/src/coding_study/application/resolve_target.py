"""A command's problem target: a slug or id, or a solution file in the workspace.

`cstudy test python/practice/two_sum.py` means `cstudy test two-sum --lang python`, so an IDE can
run any command on the file in its editor (docs/specs/cli.md#solution-file-targets).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.targets import SolutionFile, is_path_target, parse_solution_file


@dataclass(frozen=True, slots=True)
class ProblemTarget:
    slug: str
    """What the user typed: a slug, an id or a path; resolved, always a slug or an id."""
    language: Language | None = None


@dataclass(frozen=True, slots=True)
class Target:
    """A target that may be missing: the command then works on the active attempt."""

    slug: str | None = None
    language: Language | None = None


def resolve_target(environment: Environment, target: Target, cwd: Path) -> Target:
    if target.slug is None:
        return target
    resolved = resolve_problem(environment, ProblemTarget(target.slug, target.language), cwd)
    return Target(resolved.slug, resolved.language)


def resolve_problem(environment: Environment, target: ProblemTarget, cwd: Path) -> ProblemTarget:
    """`target` with a path replaced by its problem's slug and its language.

    Anything that is not a path comes back unchanged. Raises UsageError for a path that is not a
    solution file of a problem in the workspace, or that contradicts the language.
    """
    if not is_path_target(target.slug):
        return target
    solution = _solution_file(environment, target.slug, cwd)
    if target.language not in (None, solution.language):
        raise UsageError(
            f"{target.slug} is a {solution.language} file but --lang {target.language} was given"
        )
    return ProblemTarget(_slug_of(environment, solution, target.slug), solution.language)


def _solution_file(environment: Environment, text: str, cwd: Path) -> SolutionFile:
    absolute = Path(os.path.normpath(cwd / text)).resolve()
    try:
        relative = absolute.relative_to(environment.root.resolve())
    except ValueError:
        raise UsageError(_not_a_solution_file(text)) from None
    found = parse_solution_file(relative.as_posix())
    if found is None:
        raise UsageError(_not_a_solution_file(text))
    return found


def _slug_of(environment: Environment, solution: SolutionFile, text: str) -> str:
    for slug in environment.files.slugs():
        if solution.belongs_to(slug):
            return slug
    raise UsageError(f"no problem for {text}: none is named {solution.name}")


def _not_a_solution_file(text: str) -> str:
    return f"not a solution file in this workspace: {text}"
