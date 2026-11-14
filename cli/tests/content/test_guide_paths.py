"""The shipped learning paths read from introductory to advanced, "Getting started" first
(docs/specs/guides.md#path-order), as `cstudy learn` and the Guides page list them."""

from coding_study.adapters.fs_guide_catalog import FsGuideCatalog
from coding_study.domain.concept_guides import LEVEL_RANKS, GuideLevel, by_level, path_level
from tests.helpers import REPOSITORY_ROOT

FIRST_PATH = "getting-started"


def shipped_order() -> list[tuple[str, GuideLevel | None]]:
    catalog = FsGuideCatalog(REPOSITORY_ROOT)
    levels = {slug: catalog.load(slug).level for slug in catalog.slugs()}
    paths = by_level([catalog.load_path(slug) for slug in catalog.path_slugs()], levels)
    return [(path.slug, path_level(path, levels)) for path in paths]


def test_every_shipped_path_names_its_level():
    catalog = FsGuideCatalog(REPOSITORY_ROOT)
    unnamed = [slug for slug in catalog.path_slugs() if catalog.load_path(slug).level is None]
    assert unnamed == []


def test_getting_started_comes_first():
    assert shipped_order()[0] == (FIRST_PATH, GuideLevel.INTRO)


def test_no_path_comes_after_one_of_a_higher_level():
    ranks = [LEVEL_RANKS[level] for _, level in shipped_order() if level is not None]
    assert ranks == sorted(ranks)
