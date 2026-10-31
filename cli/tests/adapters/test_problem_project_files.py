"""The starter and reference trees of a project problem, read as data."""

import os
import shutil
from pathlib import Path

import pytest

from coding_study.adapters.problem_project_files import read_project_files
from coding_study.domain.errors import ContentError
from coding_study.domain.project import ProjectFile, ProjectTree
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS

SOURCE = f"problems/{BANK_PROJECT}"


@pytest.fixture
def problem(tmp_path) -> Path:
    directory = tmp_path / BANK_PROJECT
    shutil.copytree(PROJECT_PROBLEMS / BANK_PROJECT, directory)
    return directory


def issues_for(directory: Path) -> list[str]:
    with pytest.raises(ContentError) as raised:
        read_project_files(directory, SOURCE)
    return [str(issue) for issue in raised.value.issues]


def test_lists_the_starter_in_path_order(problem):
    starter = read_project_files(problem, SOURCE).starter
    assert starter is not None
    assert [file.path for file in starter.files] == ["README.md", "bank/bank.py", "pyproject.toml"]


def test_a_text_file_keeps_its_size_and_content(problem):
    (problem / "starter" / "notes.txt").write_text("café\n", encoding="utf-8")
    starter = read_project_files(problem, SOURCE).starter
    assert starter is not None
    assert starter.file("notes.txt") == ProjectFile("notes.txt", 6, "café\n")


@pytest.mark.parametrize(
    "content", [b"\x89PNG\r\n\x1a\n", b"text\x00with a NUL"], ids=["not utf-8", "nul byte"]
)
def test_a_binary_file_has_no_text(problem, content):
    (problem / "starter" / "logo.png").write_bytes(content)
    starter = read_project_files(problem, SOURCE).starter
    assert starter is not None
    assert starter.file("logo.png") == ProjectFile("logo.png", len(content), None)


def test_each_directory_in_solutions_is_an_overlay(problem):
    (problem / "solutions" / "explanation.md").write_text("# Bank\n")
    (problem / "solutions" / "draft").mkdir()
    overlays = read_project_files(problem, SOURCE).overlays
    assert set(overlays) == {"draft", "reference"}


def test_an_overlay_lists_its_files_relative_to_its_folder(problem):
    overlay = read_project_files(problem, SOURCE).overlays["reference"]
    assert overlay.paths == {"bank/bank.py"}


def test_hidden_directories_in_solutions_are_not_overlays(problem):
    (problem / "solutions" / ".cache").mkdir()
    assert set(read_project_files(problem, SOURCE).overlays) == {"reference"}


def test_a_problem_without_a_starter_has_none(problem):
    shutil.rmtree(problem / "starter")
    assert read_project_files(problem, SOURCE).starter is None


def test_a_problem_without_solutions_has_no_overlays(problem):
    shutil.rmtree(problem / "solutions")
    assert read_project_files(problem, SOURCE).overlays == {}


def test_an_empty_starter_is_an_empty_tree(problem):
    shutil.rmtree(problem / "starter")
    (problem / "starter").mkdir()
    assert read_project_files(problem, SOURCE).starter == ProjectTree(())


def test_a_link_out_of_the_starter_is_refused(problem, tmp_path):
    (tmp_path / "secret.txt").write_text("secret")
    (problem / "starter" / "bank" / "secret.txt").symlink_to(tmp_path / "secret.txt")
    assert issues_for(problem) == [
        f"{SOURCE}/starter/bank/secret.txt: is a symbolic link: a project folder holds plain "
        "files only"
    ]


def test_a_link_inside_the_starter_is_refused_too(problem):
    (problem / "starter" / "about.md").symlink_to("README.md")
    assert issues_for(problem) == [
        f"{SOURCE}/starter/about.md: is a symbolic link: a project folder holds plain files only"
    ]


def test_a_link_to_a_directory_is_never_followed(problem, tmp_path):
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "module.py").write_text("")
    (problem / "starter" / "vendor").symlink_to(tmp_path / "outside")
    assert issues_for(problem) == [
        f"{SOURCE}/starter/vendor: is a symbolic link: a project folder holds plain files only"
    ]


def test_a_starter_that_is_a_link_is_refused(problem, tmp_path):
    shutil.move(problem / "starter", tmp_path / "elsewhere")
    (problem / "starter").symlink_to(tmp_path / "elsewhere")
    assert issues_for(problem) == [
        f"{SOURCE}/starter: is a symbolic link: a project folder holds plain files only"
    ]


def test_an_overlay_that_is_a_link_is_refused(problem):
    (problem / "solutions" / "copy").symlink_to(problem / "solutions" / "reference")
    assert issues_for(problem) == [
        f"{SOURCE}/solutions/copy: is a symbolic link: a project folder holds plain files only"
    ]


def test_a_link_out_of_an_overlay_is_refused(problem):
    overlay = problem / "solutions" / "reference" / "bank"
    (overlay / "starter.py").symlink_to(problem / "starter" / "bank" / "bank.py")
    assert issues_for(problem) == [
        f"{SOURCE}/solutions/reference/bank/starter.py: is a symbolic link: a project folder "
        "holds plain files only"
    ]


def test_a_special_file_is_refused_without_being_read(problem):
    os.mkfifo(problem / "starter" / "pipe")
    assert issues_for(problem) == [f"{SOURCE}/starter/pipe: is not a plain file"]


def test_every_refused_entry_is_reported(problem):
    (problem / "starter" / "one").symlink_to("README.md")
    (problem / "solutions" / "reference" / "two").symlink_to("bank")
    assert len(issues_for(problem)) == 2
