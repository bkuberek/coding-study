"""File names inside a problem directory (docs/specs/problem-format.md#directory-layout)."""

import re
import shlex
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

WORKSPACE_ROOT = "workspace root"
CONTENT_ROOT = "content root"


@dataclass(frozen=True, slots=True)
class MisnamedDirectory:
    """A directory of `problems/` that loads as no problem until fixed by hand: its name is not a
    slug, or its meta.yaml still has an `id:` line, which is no longer a field
    (docs/specs/compatibility.md#your-own-problems)."""

    name: str
    slug: str | None
    """The name to give it: the `slug` of its meta.yaml, else its name without a leading `NNNN-`;
    None when neither is a slug. The name itself when that already is a slug."""
    root: str = WORKSPACE_ROOT
    """The root its `problems/` sits under: the workspace root or the content root."""
    stale_id: bool = False
    """Its meta.yaml has an `id:` line."""
    taken: bool = False
    """Another directory of `problems/` already has `slug` as its name, or another misnamed
    directory would be renamed to it."""

    @property
    def is_named_by_slug(self) -> bool:
        return SLUG_PATTERN.fullmatch(self.name) is not None

    def problem(self) -> str:
        """Why no problem loads from it."""
        if self.is_named_by_slug:
            return "meta.yaml still has an `id:` line, so no problem loads from it"
        return "the name is not a slug, so no problem loads from it"

    def fix(self, directory: str) -> str:
        """What to do about it, from `root`, e.g. ``from the workspace root run
        `mv problems/NNNN-two-sum problems/two-sum`, then delete the `id:` line of
        `problems/two-sum/meta.yaml```."""
        delete = "delete the `id:` line of"
        if self.is_named_by_slug:
            return f"{delete} `{directory}/{self.name}/meta.yaml` in the {self.root}"
        source = f"{directory}/{self.name}"
        if self.slug is None:
            rename = f"give `{source}` a slug"
            return f"{rename}, then {delete} its meta.yaml" if self.stale_id else rename
        if self.taken:
            rename = (
                f"`{directory}/{self.slug}` is taken: give `{source}` a free slug in the "
                f"{self.root}"
            )
            return f"{rename}, then {delete} its meta.yaml" if self.stale_id else rename
        move = f"mv {shlex.quote(source)} {shlex.quote(f'{directory}/{self.slug}')}"
        rename = f"from the {self.root} run `{move}`"
        if not self.stale_id:
            return rename
        return f"{rename}, then {delete} `{directory}/{self.slug}/meta.yaml`"


def misnamed_directory(
    name: str, meta_slug: object, root: str = WORKSPACE_ROOT, stale_id: bool = False
) -> MisnamedDirectory:
    """`name` is not a slug, or `stale_id`; `meta_slug` is what its meta.yaml says, of any type."""
    if SLUG_PATTERN.fullmatch(name):
        return MisnamedDirectory(name, name, root, stale_id)
    stripped = _NUMBER_PREFIX.sub("", name, count=1)
    for candidate in (meta_slug, stripped):
        if isinstance(candidate, str) and SLUG_PATTERN.fullmatch(candidate):
            return MisnamedDirectory(name, candidate, root, stale_id)
    return MisnamedDirectory(name, None, root, stale_id)
