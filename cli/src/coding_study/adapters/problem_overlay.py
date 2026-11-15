"""A workspace's own problems/ overlaid on the catalog
(docs/specs/installation-and-workspaces.md#your-own-problems).

The overlay is keyed by slug: a workspace problem hides every catalog problem with its slug, as a
whole directory. The summaries list in slug order.
"""

from collections.abc import Sequence
from pathlib import Path

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.problem import Problem, ProblemSummary
from coding_study.domain.problem_files import WORKSPACE_ROOT, MisnamedDirectory


class OverlayProblemRepository:
    """`ProblemRepository` over the catalog and the workspace's own problems."""

    def __init__(self, catalog: FsProblemRepository, workspace: Path) -> None:
        self._catalog = catalog
        self._own = catalog.over(workspace)

    def load(self, slug: str) -> Problem:
        owner = self._own if slug in self._own.slugs() else self._catalog
        return owner.load(slug)

    def list_summaries(self) -> tuple[ProblemSummary, ...]:
        own_slugs = set(self._own.slugs())
        issues: list[ContentIssue] = []
        own = _summaries(self._own, issues)
        catalog = [s for s in _summaries(self._catalog, issues) if s.meta.slug not in own_slugs]
        if issues:
            raise ContentError(issues)
        return tuple(sorted((*catalog, *own), key=lambda summary: summary.meta.slug))


class OverlayProblemFiles:
    """`ProblemFiles` over the catalog and the workspace's own problems."""

    def __init__(self, catalog: FsProblemFiles, workspace: Path) -> None:
        self._catalog = catalog
        self._own = FsProblemFiles(workspace, catalog.directory, WORKSPACE_ROOT)

    @property
    def directory(self) -> str:
        return self._catalog.directory

    def slugs(self) -> tuple[str, ...]:
        """The catalog's problems, without the hidden ones, and your own, in name order."""
        own = self._own.slugs()
        return tuple(sorted((*(slug for slug in self._catalog.slugs() if slug not in own), *own)))

    def misnamed(self) -> tuple[MisnamedDirectory, ...]:
        return tuple(
            sorted((*self._catalog.misnamed(), *self._own.misnamed()), key=lambda found: found.name)
        )

    def problem_directory(self, slug: str) -> str:
        return self._owner(slug).problem_directory(slug)

    def read_text(self, slug: str, name: str) -> str | None:
        return self._owner(slug).read_text(slug, name)

    def file_names(self, slug: str, directory: str = "") -> tuple[str, ...]:
        return self._owner(slug).file_names(slug, directory)

    def path(self, slug: str, name: str) -> Path:
        return self._owner(slug).path(slug, name)

    def fingerprint(self, slug: str, names: Sequence[str]) -> str:
        return self._owner(slug).fingerprint(slug, names)

    def _owner(self, slug: str) -> FsProblemFiles:
        return self._own if slug in self._own.slugs() else self._catalog


def _summaries(
    repository: FsProblemRepository, issues: list[ContentIssue]
) -> tuple[ProblemSummary, ...]:
    try:
        return repository.list_summaries()
    except ContentError as error:
        issues.extend(error.issues)
        return ()
