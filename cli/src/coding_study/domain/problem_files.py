"""File names inside a problem directory (docs/specs/problem-format.md#directory-layout)."""

import re
from dataclasses import dataclass

from coding_study.domain.problem import SLUG_PATTERN

META_FILE = "meta.yaml"
TESTS_FILE = "tests.json"
PROBLEM_FILE = "problem.md"
GENERATOR_FILE = "generator.py"
CHECKER_FILE = "checker.py"
STRESS_CHECKER_FILE = "stress_checker.py"
RUBRIC_FILE = "rubric.md"
BUGGY_DIRECTORY = "buggy"
HELPERS_DIRECTORY = "helpers"
"""Generated starters: at most one file per language that the language's starter ends with."""
STARTER_DIRECTORY = "starter"
"""Project problems: the seeded folder `cstudy start` copies into the workspace."""
SOLUTIONS_DIRECTORY = "solutions"
EXPLANATION_NAME = "explanation.md"
EXPLANATION_FILE = f"{SOLUTIONS_DIRECTORY}/{EXPLANATION_NAME}"
BROKEN_DIRECTORY = f"{SOLUTIONS_DIRECTORY}/broken"
"""Concurrent problems: `<broken-id>.<ext>`, deliberately wrong references."""


def solution_file(file_name: str) -> str:
    """`solutions/<file_name>`, relative to the problem directory."""
    return f"{SOLUTIONS_DIRECTORY}/{file_name}"


def broken_file(file_name: str) -> str:
    """`solutions/broken/<file_name>`, relative to the problem directory."""
    return f"{BROKEN_DIRECTORY}/{file_name}"


_NUMBER_PREFIX = re.compile(r"[0-9]{4}-")


@dataclass(frozen=True, slots=True)
class MisnamedDirectory:
    """A directory of `problems/` whose name is not a slug, so no problem loads from it
    (docs/specs/compatibility.md#your-own-problems)."""

    name: str
    slug: str | None
    """The name to give it: the `slug` of its meta.yaml, else its name without a leading `NNNN-`;
    None when neither is a slug."""

    def rename(self, directory: str) -> str | None:
        """The command that renames it, run from the workspace root, e.g.
        `mv problems/NNNN-two-sum problems/two-sum`; None without a slug to name it by."""
        if self.slug is None:
            return None
        return f"mv {directory}/{self.name} {directory}/{self.slug}"


def misnamed_directory(name: str, meta_slug: object) -> MisnamedDirectory:
    """`name` is not a slug; `meta_slug` is what its meta.yaml says, of any type."""
    stripped = _NUMBER_PREFIX.sub("", name, count=1)
    for candidate in (meta_slug, stripped):
        if isinstance(candidate, str) and SLUG_PATTERN.fullmatch(candidate):
            return MisnamedDirectory(name, candidate)
    return MisnamedDirectory(name, None)
