"""`cstudy learn` (docs/specs/cli.md#cstudy-learn): the concept guides and learning paths, and how
far a learner has come (docs/specs/guides.md#reading-progress)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.domain.concept_guides import (
    DIAGRAMS_DIRECTORY,
    GuideLevel,
    GuideMeta,
    GuideStatus,
    LearningPath,
    PathStep,
    ProblemFacts,
    StepKind,
    StepProgress,
    by_level,
    guide_step_progress,
    highest_level_passed,
    matches_search,
    path_level,
    problem_step_progress,
    search_words,
    unknown_slug_message,
)
from coding_study.domain.errors import UnknownGuideError
from coding_study.domain.guide_examples import PYTHON, LanguageChoice, terminal_text
from coding_study.domain.guide_markdown import GuideMarkdown, is_svg_file
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
    level: GuideLevel | None = None
    """The level the path is for, from its guides' levels (docs/specs/guides.md#path-order);
    None for a path without guides."""

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
    """From introductory to advanced (docs/specs/guides.md#path-order)."""


@dataclass(frozen=True, slots=True)
class ListingFilter:
    """`cstudy learn --search --level --status` (docs/specs/cli.md#cstudy-learn)."""

    search: str = ""
    level: GuideLevel | None = None
    status: GuideStatus | None = None

    @property
    def narrows(self) -> bool:
        return bool(search_words(self.search)) or self.level is not None or self.status is not None


@dataclass(frozen=True, slots=True)
class GuidePage:
    entry: GuideEntry
    markdown: str
    """guide.md as written."""
    examples: tuple[Path, ...]
    """The absolute path of every example."""
    examples_folder: Path | None
    """None for a guide without examples."""
    diagrams: Mapping[str, str] = field(default_factory=dict[str, str])
    """The SVG drawings of its diagrams, by path relative to the guide (`diagrams/1-light.svg`)."""
    language: str | None = None
    """The language chosen for its examples (`--lang`); None: none chosen."""
    default_language: str = PYTHON
    """The config's `default_lang`."""

    def terminal_text(self, others_hint: str = "") -> str:
        """The guide with each diagram shown as its text drawing, and each example with variants
        in the language shown (docs/specs/guides.md#the-language-shown), followed by its other
        languages and `others_hint`, the command that picks one."""
        choice = LanguageChoice(self.language, self.default_language, others_hint)
        return terminal_text(GuideMarkdown(self.markdown), choice)


@dataclass(frozen=True, slots=True)
class MarkedRead:
    slug: str
    read_at: datetime
    already: bool
    """It had been marked before; nothing changed."""


def learn_listing(environment: Environment) -> LearnListing:
    catalog = environment.guides
    reads = environment.progress.guide_reads()
    metas = {slug: catalog.load(slug) for slug in catalog.slugs()}
    levels = {slug: meta.level for slug, meta in metas.items()}
    loaded = [catalog.load_path(slug) for slug in catalog.path_slugs()]
    progress = _Progress(environment)
    paths = tuple(_path_view(progress, path, levels) for path in by_level(loaded, levels))
    in_paths = [
        step.step.slug for view in paths for step in view.steps if step.step.kind is StepKind.GUIDE
    ]
    order = list(dict.fromkeys((*in_paths, *metas)))
    guides = tuple(GuideEntry(metas[slug], reads.get(slug)) for slug in order if slug in metas)
    return LearnListing(guides, paths)


def narrow_listing(listing: LearnListing, wanted: ListingFilter) -> LearnListing:
    """The guides and the paths that hold every word of the search in their title, summary or
    slug, at the level and in the status asked, each list in its order; the Guides page's search
    and filters keep the same (`tools/web-ui/src/page/guides-model.ts`)."""
    words = search_words(wanted.search)
    read = {entry.meta.slug for entry in listing.guides if entry.read_at is not None}

    def guide_kept(entry: GuideEntry) -> bool:
        meta = entry.meta
        status = GuideStatus.READ if entry.read_at is not None else GuideStatus.NOT_READ
        return (
            matches_search(words, meta.title, meta.summary, meta.slug)
            and wanted.level in (None, meta.level)
            and wanted.status in (None, status)
        )

    def path_kept(view: PathView) -> bool:
        path = view.path
        return (
            matches_search(words, path.title, path.summary, path.slug)
            and wanted.level in (None, view.level)
            and wanted.status in (None, _path_status(path, read))
        )

    return LearnListing(
        tuple(entry for entry in listing.guides if guide_kept(entry)),
        tuple(view for view in listing.paths if path_kept(view)),
    )


def _path_status(path: LearningPath, read: set[str]) -> GuideStatus | None:
    """Read once every guide it has is read, not read while one is not; None without guides."""
    guides = [step.slug for step in path.steps if step.kind is StepKind.GUIDE]
    if not guides:
        return None
    return GuideStatus.READ if all(slug in read for slug in guides) else GuideStatus.NOT_READ


def guide_page(environment: Environment, slug: str, language: str | None = None) -> GuidePage:
    """`language` is the one chosen for the examples. Raises UnknownGuideError for a guide that
    does not exist, ContentError for one that does not load."""
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
        diagrams=catalog.diagrams(slug),
        language=language,
        default_language=environment.config.default_lang.value,
    )


def guide_drawing(environment: Environment, slug: str, name: str) -> str:
    """The SVG drawing `name`, such as `1-dark.svg`, of a guide's diagram. Raises
    UnknownGuideError for a guide that does not exist or a drawing it does not have."""
    catalog = environment.guides
    _require(slug, catalog.slugs(), "guide")
    drawing = (
        catalog.diagrams(slug).get(f"{DIAGRAMS_DIRECTORY}/{name}") if is_svg_file(name) else None
    )
    if drawing is None:
        raise UnknownGuideError(f'guide "{slug}" has no drawing "{name}"')
    return drawing


def mark_read(environment: Environment, slug: str) -> MarkedRead:
    """`--done`: the first time is kept."""
    _require(slug, environment.guides.slugs(), "guide")
    now = environment.clock.now()
    earlier = environment.progress.mark_guide_read(slug, now)
    return MarkedRead(slug, earlier or now, already=earlier is not None)


def path_view(environment: Environment, slug: str) -> PathView:
    """Raises UnknownGuideError for a path that does not exist, ContentError for one that does not
    load."""
    catalog = environment.guides
    _require(slug, catalog.path_slugs(), "path")
    path = catalog.load_path(slug)
    known = catalog.slugs()
    guides = {step.slug for step in path.steps if step.kind is StepKind.GUIDE}
    levels = {guide: catalog.load(guide).level for guide in guides if guide in known}
    return _path_view(_Progress(environment), path, levels)


def guide_entries(environment: Environment, slugs: tuple[str, ...]) -> tuple[GuideEntry, ...]:
    """The guides of `slugs` that exist, in that order, each with whether it is read: a
    problem's `guides` as the Problem view lists them."""
    catalog = environment.guides
    known = catalog.slugs()
    reads = environment.progress.guide_reads()
    return tuple(GuideEntry(catalog.load(slug), reads.get(slug)) for slug in slugs if slug in known)


def _require(slug: str, known: tuple[str, ...], noun: str) -> None:
    if slug not in known:
        raise UnknownGuideError(unknown_slug_message(noun, slug, known))


def _path_view(
    progress: "_Progress", path: LearningPath, levels: Mapping[str, GuideLevel]
) -> PathView:
    return PathView(path, tuple(progress.of(step) for step in path.steps), path_level(path, levels))


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
