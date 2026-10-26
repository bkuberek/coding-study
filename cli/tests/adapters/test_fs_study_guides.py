from pathlib import Path

import pytest

from coding_study.adapters.fs_study_guides import FsStudyGuides

GUIDE = "distributed-systems.md"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    guides = tmp_path / "study-guides"
    (guides / "nested").mkdir(parents=True)
    (guides / GUIDE).write_text("# Distributed systems\n")
    (guides / "nested" / "caching.md").write_text("# Caching\n")
    (tmp_path / "outside.md").write_text("# Not a guide\n")
    return guides


def test_without_a_root_no_guide_is_located():
    assert FsStudyGuides(None).locate(GUIDE) is None


def test_an_existing_guide_is_located_as_a_file_uri(root):
    assert FsStudyGuides(root).locate(GUIDE) == (root / GUIDE).as_uri()


def test_a_guide_in_a_subdirectory_is_located(root):
    assert FsStudyGuides(root).locate("nested/caching.md") == (root / "nested/caching.md").as_uri()


def test_a_missing_guide_is_not_located(root):
    assert FsStudyGuides(root).locate("missing.md") is None


def test_a_directory_is_not_a_guide(root):
    assert FsStudyGuides(root).locate("nested") is None


def test_a_path_outside_the_root_is_not_located(root):
    assert FsStudyGuides(root).locate("../outside.md") is None


def test_a_tilde_setting_is_relative_to_home(root):
    guides = FsStudyGuides.from_setting("~/study-guides", root.parent)
    assert guides.locate(GUIDE) == (root / GUIDE).as_uri()


def test_an_absolute_setting_is_used_as_is(root):
    assert FsStudyGuides.from_setting(str(root), Path("/elsewhere")).locate(GUIDE) is not None


def test_no_setting_locates_nothing(root):
    assert FsStudyGuides.from_setting(None, root.parent).locate(GUIDE) is None
