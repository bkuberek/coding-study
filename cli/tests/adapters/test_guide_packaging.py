"""guides/ ships in the sdist and the wheel, at coding_study/content/guides beside the problems
(docs/specs/installation-and-workspaces.md#install)."""

import tomllib
from pathlib import Path

from coding_study.adapters.fs_guide_catalog import FsGuideCatalog
from coding_study.adapters.locations import find_content_root
from tests.guide_builders import write_hashing
from tests.helpers import REPOSITORY_ROOT

BUILD = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text())["tool"]["hatch"]["build"]


def test_the_sdist_and_the_wheel_include_the_guides():
    targets = BUILD["targets"]
    assert (
        "guides" in targets["sdist"]["only-include"],
        "guides" in targets["wheel"]["only-include"],
        targets["wheel"]["sources"]["guides"],
    ) == (True, True, "coding_study/content/guides")


def test_the_bundled_copy_holds_the_guides_cstudy_reads(content_root: Path, tmp_path: Path):
    package = tmp_path / "site-packages" / "coding_study"
    bundled = package / "content"
    bundled.mkdir(parents=True)
    write_hashing(content_root)
    for name in ("problems", "schemas", "guides"):
        (bundled / name).symlink_to(content_root / name, target_is_directory=True)
    root = find_content_root({}, package)
    assert FsGuideCatalog(root.path).path_slugs() == ("hashing",)
