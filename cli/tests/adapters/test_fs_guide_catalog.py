from pathlib import Path

import pytest

from coding_study.adapters.fs_guide_catalog import FsGuideCatalog
from coding_study.domain.concept_guides import GuideLevel, GuideMeta, LearningPath, PathStep
from coding_study.domain.errors import ContentError
from tests.guide_builders import EXAMPLE, write_guide, write_hashing, write_path


def test_a_root_without_guides_has_none(content_root: Path):
    catalog = FsGuideCatalog(content_root)
    assert (catalog.slugs(), catalog.path_slugs()) == ((), ())


def test_guides_are_the_folders_of_guides_but_paths(content_root: Path):
    write_hashing(content_root)
    (content_root / "guides" / ".hidden").mkdir()
    assert FsGuideCatalog(content_root).slugs() == ("hash-functions", "hash-maps")


def test_a_guide_loads_its_meta_with_its_folder_as_slug(content_root: Path):
    write_hashing(content_root)
    assert FsGuideCatalog(content_root).load("hash-maps") == GuideMeta(
        slug="hash-maps",
        title="Hash maps",
        summary="A short summary.",
        level=GuideLevel.INTRO,
        prerequisites=("hash-functions",),
        problems=("two-sum",),
    )


def test_a_meta_that_fails_its_schema_is_a_content_error(content_root: Path):
    write_guide(content_root, "broken", "Broken", level="expert")
    with pytest.raises(ContentError) as error:
        FsGuideCatalog(content_root).load("broken")
    assert str(error.value).startswith("guides/broken/meta.yaml: level: ")


def test_files_lists_every_file_but_hidden_ones(content_root: Path):
    folder = write_guide(content_root, "hash-maps", "Hash maps")
    (folder / ".DS_Store").write_text("")
    (folder / "examples" / "__pycache__").mkdir()
    (folder / "examples" / "__pycache__" / "x.pyc").write_text("")
    assert FsGuideCatalog(content_root).files("hash-maps") == (
        "examples/hello.py",
        "guide.md",
        "meta.yaml",
    )


def test_examples_are_read_by_their_path_in_the_guide(content_root: Path):
    write_guide(content_root, "hash-maps", "Hash maps")
    assert FsGuideCatalog(content_root).examples("hash-maps") == {"examples/hello.py": EXAMPLE}


def test_a_missing_guide_md_reads_as_none(content_root: Path):
    folder = write_guide(content_root, "hash-maps", "Hash maps")
    (folder / "guide.md").unlink()
    assert FsGuideCatalog(content_root).read_guide("hash-maps") is None


def test_a_path_loads_its_steps_in_order(content_root: Path):
    write_hashing(content_root)
    assert FsGuideCatalog(content_root).load_path("hashing") == LearningPath(
        slug="hashing",
        title="Hashing",
        summary="From hash functions on.",
        steps=(
            PathStep.guide("hash-functions"),
            PathStep.guide("hash-maps"),
            PathStep.problem("two-sum"),
            PathStep.problem("tamper-evident-ledger", 2),
        ),
    )


def test_a_step_that_is_neither_a_guide_nor_a_problem_fails_the_schema(content_root: Path):
    write_path(content_root, "odd", ["{guide: hash-maps, level: 2}"])
    with pytest.raises(ContentError) as error:
        FsGuideCatalog(content_root).load_path("odd")
    assert str(error.value).startswith("guides/paths/odd.yaml: steps[0]: ")


def test_locations_are_repository_relative(content_root: Path):
    catalog = FsGuideCatalog(content_root)
    assert (catalog.guide_directory("a"), catalog.path_file("b")) == (
        "guides/a",
        "guides/paths/b.yaml",
    )
