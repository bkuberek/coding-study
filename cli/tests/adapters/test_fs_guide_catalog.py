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
        domains=("algorithms",),
        job_roles=("general",),
        prerequisites=("hash-functions",),
        problems=("two-sum",),
    )


def test_a_guide_loads_its_domains_and_job_roles(content_root: Path):
    write_guide(
        content_root,
        "hash-maps",
        "Hash maps",
        domains=("algorithms", "backend"),
        job_roles=("general",),
    )
    meta = FsGuideCatalog(content_root).load("hash-maps")
    assert (meta.domains, meta.job_roles) == (("algorithms", "backend"), ("general",))


@pytest.mark.parametrize(
    ("domains", "job_roles", "missing"),
    [((), ("general",), "domains"), (("algorithms",), (), "job_roles")],
)
def test_a_guide_without_a_label_list_is_a_content_error(
    content_root: Path, domains: tuple[str, ...], job_roles: tuple[str, ...], missing: str
):
    write_guide(content_root, "hash-maps", "Hash maps", domains=domains, job_roles=job_roles)
    with pytest.raises(ContentError) as error:
        FsGuideCatalog(content_root).load("hash-maps")
    assert str(error.value).startswith("guides/hash-maps/meta.yaml: ")
    assert f"'{missing}' is a required property" in str(error.value)


@pytest.mark.parametrize(
    ("domains", "job_roles", "location"),
    [
        (("physics",), ("general",), "domains[0]"),
        (("algorithms", "algorithms"), ("general",), "domains"),
        (("algorithms",), ("wizard",), "job_roles[0]"),
        (("algorithms",), ("backend", "backend"), "job_roles"),
    ],
)
def test_a_label_outside_its_list_or_listed_twice_is_a_content_error(
    content_root: Path, domains: tuple[str, ...], job_roles: tuple[str, ...], location: str
):
    write_guide(content_root, "broken", "Broken", domains=domains, job_roles=job_roles)
    with pytest.raises(ContentError) as error:
        FsGuideCatalog(content_root).load("broken")
    assert str(error.value).startswith(f"guides/broken/meta.yaml: {location}: ")


def test_a_shell_guide_says_so_in_its_meta(content_root: Path):
    folder = write_guide(content_root, "using-the-terminal", "Using the terminal")
    with (folder / "meta.yaml").open("a") as meta:
        meta.write("shell: true\n")
    catalog = FsGuideCatalog(content_root)
    write_guide(content_root, "hash-maps", "Hash maps")
    assert (catalog.load("using-the-terminal").shell, catalog.load("hash-maps").shell) == (
        True,
        False,
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
        "diagrams/1-dark.svg",
        "diagrams/1-light.svg",
        "examples/hello.py",
        "guide.md",
        "meta.yaml",
    )


def test_examples_are_read_by_their_path_in_the_guide(content_root: Path):
    write_guide(content_root, "hash-maps", "Hash maps")
    assert FsGuideCatalog(content_root).examples("hash-maps") == {"examples/hello.py": EXAMPLE}


def test_svg_drawings_are_read_by_their_path_in_the_guide(content_root: Path):
    write_guide(content_root, "hash-maps", "Hash maps")
    drawings = FsGuideCatalog(content_root).diagrams("hash-maps")
    assert (
        sorted(drawings),
        drawings["diagrams/1-dark.svg"].startswith("<!-- svg-of-mermaid"),
    ) == (
        ["diagrams/1-dark.svg", "diagrams/1-light.svg"],
        True,
    )


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


def test_a_path_loads_the_level_it_names(content_root: Path):
    write_hashing(content_root)
    write_path(content_root, "deep", ["guide: hash-maps"], level="advanced")
    catalog = FsGuideCatalog(content_root)
    assert (catalog.load_path("deep").level, catalog.load_path("hashing").level) == (
        GuideLevel.ADVANCED,
        None,
    )


def test_a_path_level_that_is_no_guide_level_fails_the_schema(content_root: Path):
    write_path(content_root, "odd", ["guide: hash-maps"], level="expert")
    with pytest.raises(ContentError) as error:
        FsGuideCatalog(content_root).load_path("odd")
    assert str(error.value).startswith("guides/paths/odd.yaml: level: ")


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
