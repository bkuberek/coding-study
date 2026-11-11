"""`cstudy learn` (docs/specs/cli.md#cstudy-learn): the concept guides and learning paths, and how
far a learner has come (docs/specs/guides.md#reading-progress)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.domain.concept_guides import (
    GuideMeta,
    LearningPath,
    PathStep,
    ProblemFacts,
    StepKind,
    StepProgress,
    guide_step_progress,
    highest_level_passed,
    problem_step_progress,
    unknown_slug_message,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.guide_markdown import GuideMarkdown
from coding_study.domain.problem import ProblemSummary
from coding_study.domain.problem_sets import target_reached
from coding_study.domain.scheduling import ProblemProgress

MISSING = "missing"
"""The status of a path step whose problem the catalog does not have."""


@dataclass(frozen=True, slots=True)
class GuideEntry:
    meta: GuideMeta
    read_at: datetime | None
    """When it was first marked read; None while it is not."""


@dataclass(frozen=True, slots=True)
class PathView:
    path: LearningPath
    steps: tuple[StepProgress, ...]

    @property
    def done(self) -> int:
        return sum(1 for step in self.steps if step.done)

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def next_step(self) -> StepProgress | None:
        return next((step for step in self.steps if not step.done), None)


@dataclass(frozen=True, slots=True)
class LearnListing:
    guides: tuple[GuideEntry, ...]
    """In the order of the paths, then by slug."""
    paths: tuple[PathView, ...]


@dataclass(frozen=True, slots=True)
class GuidePage:
    entry: GuideEntry
    markdown: str
    """guide.md as written."""
    examples: tuple[Path, ...]
    """The absolute path of every example."""
    examples_folder: Path | None
    """None for a guide without examples."""

    @property
    def terminal_text(self) -> str:
        """The guide with each diagram shown as its text drawing."""
        return GuideMarkdown(self.markdown).terminal_text()


@dataclass(frozen=True, slots=True)
class MarkedRead:
    slug: str
    read_at: datetime
    already: bool
    """It had been marked before; nothing changed."""


def learn_listing(environment: Environment) -> LearnListing:
    catalog = environment.guides
    reads = environment.progress.guide_reads()
    paths = tuple(_path_view(environment, catalog.load_path(slug)) for slug in catalog.path_slugs())
    in_paths = [
        step.step.slug for view in paths for step in view.steps if step.step.kind is StepKind.GUIDE
    ]
    order = list(dict.fromkeys((*in_paths, *catalog.slugs())))
    guides = tuple(
        GuideEntry(catalog.load(slug), reads.get(slug)) for slug in order if slug in catalog.slugs()
    )
    return LearnListing(guides, paths)


def guide_page(environment: Environment, slug: str) -> GuidePage:
    """Raises UsageError for a guide that does not exist, ContentError for one that does not
    load."""
    catalog = environment.guides
    _require(slug, catalog.slugs(), "guide")
    meta = catalog.load(slug)
    folder = catalog.examples_folder(slug)
    examples = tuple(folder.parent / name for name in catalog.examples(slug))
    return GuidePage(
        entry=GuideEntry(meta, environment.progress.guide_reads().get(slug)),
        markdown=catalog.read_guide(slug) or "",
        examples=examples,
        examples_folder=folder if examples else None,
    )


def mark_read(environment: Environment, slug: str) -> MarkedRead:
    """`--done`: the first time is kept."""
    _require(slug, environment.guides.slugs(), "guide")
    now = environment.clock.now()
    earlier = environment.progress.mark_guide_read(slug, now)
    return MarkedRead(slug, earlier or now, already=earlier is not None)


def path_view(environment: Environment, slug: str) -> PathView:
    """Raises UsageError for a path that does not exist, ContentError for one that does not
    load."""
    catalog = environment.guides
    _require(slug, catalog.path_slugs(), "path")
    return _path_view(environment, catalog.load_path(slug))


def _require(slug: str, known: tuple[str, ...], noun: str) -> None:
    if slug not in known:
        raise UsageError(unknown_slug_message(noun, slug, known))


def _path_view(environment: Environment, path: LearningPath) -> PathView:
    progress = _Progress(environment)
    return PathView(path, tuple(progress.of(step) for step in path.steps))


class _Progress:
    def __init__(self, environment: Environment) -> None:
        self._environment = environment
        self._reads = environment.progress.guide_reads()
        self._problems: Mapping[str, ProblemProgress] = environment.progress.problem_progress()
        self._summaries: dict[str, ProblemSummary] | None = None
        self._today = environment.clock.local_date(environment.clock.now())

    def of(self, step: PathStep) -> StepProgress:
        if step.kind is StepKind.GUIDE:
            catalog = self._environment.guides
            title = catalog.load(step.slug).title if step.slug in catalog.slugs() else step.slug
            return guide_step_progress(step, title, step.slug in self._reads)
        summary = self._summary(step.slug)
        if summary is None:
            return StepProgress(step, step.slug, done=False, status=MISSING)
        return problem_step_progress(step, self._facts(summary))

    def _facts(self, summary: ProblemSummary) -> ProblemFacts:
        meta = summary.meta
        progress = self._problems.get(meta.slug, ProblemProgress())
        attempts = self._environment.progress.attempts(meta.slug) if meta.levels else ()
        status = progress.status(self._today)
        return ProblemFacts(
            title=meta.title,
            status=status,
            passed=target_reached(progress, len(meta.levels) or None, None),
            level_passed=highest_level_passed(attempts, len(meta.levels)),
        )

    def _summary(self, slug: str) -> ProblemSummary | None:
        if self._summaries is None:
            summaries = self._environment.problems.list_summaries()
            self._summaries = {summary.meta.slug: summary for summary in summaries}
        return self._summaries.get(slug)
