"""A command's problem target: a slug or id, or a solution file in the workspace.

`cstudy test python/practice/two_sum.py` means `cstudy test two-sum --lang python`, so an IDE can
run any command on the file in its editor (docs/specs/cli.md#solution-file-targets). Any file in a
project folder (`projects/<slug>/`) is a solution file of that folder's problem, in its language.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.targets import is_path_target, parse_solution_file
from coding_study.domain.workspace_projects import folder_language, project_slug


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

    Anything that is not a path comes back unchanged. Raises UsageError for a directory, for a path
    that is not a solution file of a problem in the workspace, or that contradicts the language.
    """
    if not is_path_target(target.slug):
        return target
    path = _workspace_path(environment, target.slug, cwd)
    slug = project_slug(path)
    found = (
        _project_file(environment, slug, target.slug)
        if slug is not None
        else _practice_file(environment, path, target.slug)
    )
    if target.language not in (None, found.language):
        raise UsageError(
            f"{target.slug} is a {found.language} file but --lang {target.language} was given"
        )
    return found


def _workspace_path(environment: Environment, text: str, cwd: Path) -> str:
    """`text` relative to the workspace root, links resolved."""
    absolute = Path(os.path.normpath(cwd / text)).resolve()
    if absolute.is_dir():
        raise UsageError(_directory(text))
    try:
        return absolute.relative_to(environment.root.resolve()).as_posix()
    except ValueError:
        raise UsageError(_not_a_solution_file(text)) from None


def _practice_file(environment: Environment, path: str, text: str) -> ProblemTarget:
    solution = parse_solution_file(path)
    if solution is None:
        raise UsageError(_not_a_solution_file(text))
    for slug in environment.files.slugs():
        if solution.belongs_to(slug):
            return ProblemTarget(slug, solution.language)
    raise UsageError(f"no problem for {text}: none is named {solution.name}")


def _project_file(environment: Environment, slug: str, text: str) -> ProblemTarget:
    if slug not in environment.files.slugs():
        raise UsageError(f"no problem for {text}: none is named {slug}")
    language = folder_language(environment.problems.load(slug).meta)
    if language is None:
        raise UsageError(f"{_not_a_solution_file(text)} ({slug} is not a project problem)")
    return ProblemTarget(slug, language)


def _not_a_solution_file(text: str) -> str:
    return f"not a solution file in this workspace: {text}"


def _directory(text: str) -> str:
    """An IDE passes the project directory for the current file when no editor has focus."""
    return f"open a solution file in the editor first (got a directory: {text})"
