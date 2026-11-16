"""`cstudy verify` on concept guides and learning paths (docs/specs/guides.md#static-checks):
static checks only, G1 to G12 and P1 to P5, one result per guide and per path."""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.domain.concept_guides import GuideMeta, LearningPath
from coding_study.domain.errors import ContentError
from coding_study.domain.guide_checks import (
    CatalogFacts,
    GuideContent,
    guide_label_warnings,
    guide_static_checks,
    guide_static_warnings,
    path_static_checks,
)


@dataclass(frozen=True, slots=True)
class GuideVerification:
    directory: str
    """A guide's folder or a path's file, repository-relative."""
    static_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    """G11's and G12's, which fail nothing."""


def verify_guides(
    environment: Environment, problem_slugs: Collection[str]
) -> tuple[GuideVerification, ...]:
    """`problem_slugs`: every problem; those a path gives a level are loaded for their levels."""
    catalog = environment.guides
    guides: dict[str, GuideMeta] = {}
    failures: dict[str, tuple[str, ...]] = {}
    for slug in catalog.slugs():
        try:
            guides[slug] = catalog.load(slug)
        except ContentError as error:
            failures[slug] = tuple(str(issue) for issue in error.issues)
    paths: dict[str, LearningPath | tuple[str, ...]] = {}
    for slug in catalog.path_slugs():
        try:
            paths[slug] = catalog.load_path(slug)
        except ContentError as error:
            paths[slug] = tuple(str(issue) for issue in error.issues)
    facts = CatalogFacts(guides, _problem_levels(environment, problem_slugs, paths))
    domains = _problem_domains(environment, guides.values())
    results = [
        GuideVerification(catalog.guide_directory(slug), failures[slug])
        if slug in failures
        else _verify_guide(environment, guides[slug], facts, domains)
        for slug in catalog.slugs()
    ]
    for slug, path in paths.items():
        file = catalog.path_file(slug)
        if isinstance(path, tuple):
            results.append(GuideVerification(file, path))
        else:
            issues = path_static_checks(file, path, facts)
            results.append(GuideVerification(file, tuple(str(issue) for issue in issues)))
    return tuple(results)


def _verify_guide(
    environment: Environment,
    meta: GuideMeta,
    facts: CatalogFacts,
    problem_domains: Mapping[str, tuple[str, ...]],
) -> GuideVerification:
    catalog = environment.guides
    directory = catalog.guide_directory(meta.slug)
    content = GuideContent(
        directory=directory,
        meta=meta,
        markdown=catalog.read_guide(meta.slug),
        files=catalog.files(meta.slug),
        examples=catalog.examples(meta.slug),
        diagrams=catalog.diagrams(meta.slug),
    )
    issues = guide_static_checks(content, facts)
    warnings = (*guide_static_warnings(content), *guide_label_warnings(content, problem_domains))
    return GuideVerification(directory, tuple(map(str, issues)), warnings=tuple(map(str, warnings)))


def _problem_domains(
    environment: Environment, guides: Iterable[GuideMeta]
) -> dict[str, tuple[str, ...]]:
    """The domains of every problem, rubric ones too, for G12; none when a problem does not load:
    its own line reports why. Read only when a guide names a problem."""
    if not any(guide.problems for guide in guides):
        return {}
    try:
        summaries = environment.problems.list_summaries()
        items = environment.items.list_items()
    except ContentError:
        return {}
    labels = [(summary.meta.slug, summary.meta.labels) for summary in summaries]
    labels.extend((item.slug, item.labels) for item in items)
    return {slug: found.domains for slug, found in labels}


def _problem_levels(
    environment: Environment,
    problem_slugs: Collection[str],
    paths: Mapping[str, LearningPath | tuple[str, ...]],
) -> dict[str, int]:
    """Every problem with no levels, but those a path gives a level, which are loaded. One that
    does not load counts as having none: its own line reports why."""
    levels = dict.fromkeys(problem_slugs, 0)
    leveled = {
        step.slug
        for path in paths.values()
        if isinstance(path, LearningPath)
        for step in path.steps
        if step.level is not None and step.slug in levels
    }
    for slug in leveled:
        try:
            levels[slug] = len(environment.problems.load(slug).meta.levels)
        except ContentError:
            continue
    return levels
