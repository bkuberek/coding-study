"""A project problem's folder in the workspace (docs/specs/cli.md#cstudy-start,
installation-and-workspaces.md#project-folders)."""

import os
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.application.project_workspace import (
    SeededProject,
    archive_project,
    resume_project,
    seed_project,
)
from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus
from coding_study.domain.errors import ContentError, UsageError
from coding_study.domain.problem import Language, Problem
from coding_study.domain.project import ProjectFile, ProjectFiles, ProjectTree
from tests.fakes import repository_root
from tests.helpers import CATALOG_PROBLEMS, PROJECT_PROBLEMS, RUST_PROJECT_PROBLEMS

SLUG = "bank-project-python"
FOLDER = f"projects/{SLUG}"
STARTER = ("README.md", "bank/bank.py", "pyproject.toml")
VENV_LINK = f"{FOLDER}/.venv"
VENV_TARGET = Path("../../python/.venv")
GO_WORK = f"{FOLDER}/go.work"
ARCHIVE = f".archive/{SLUG}/3-python"
PILOT = "0249-bank-project-python"


@pytest.fixture(scope="module")
def problem(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("content"), PROJECT_PROBLEMS)
    return FsProblemRepository(root).load(SLUG)


@pytest.fixture
def workspace(tmp_path: Path) -> WorkspaceFs:
    return WorkspaceFs(tmp_path / "ws")


def starter_text(problem: Problem, path: str) -> str | None:
    starter = (problem.project_files or ProjectFiles(None)).starter
    file = None if starter is None else starter.file(path)
    return None if file is None else file.text


def files_in(workspace: WorkspaceFs, folder: str) -> set[str]:
    root = workspace.absolute(folder)
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def owner(attempt_id: int = 3) -> Attempt:
    started = datetime(2026, 10, 30, tzinfo=UTC)
    return Attempt(
        attempt_id, SLUG, Language.PYTHON, AttemptMode.NEW, AttemptStatus.IN_PROGRESS, started
    )


# a new attempt


def test_a_new_attempt_copies_every_starter_file(workspace, problem):
    seed_project(workspace, problem)
    assert files_in(workspace, FOLDER) == set(STARTER)


def test_a_copied_file_holds_the_starter_text(workspace, problem):
    seed_project(workspace, problem)
    assert workspace.read_text(f"{FOLDER}/bank/bank.py") == starter_text(problem, "bank/bank.py")


def test_seeding_reports_the_folder_the_copied_files_and_the_link(workspace, problem):
    assert seed_project(workspace, problem) == SeededProject(FOLDER, STARTER, linked=True)


def test_a_python_folder_links_to_the_workspace_venv(workspace, problem):
    seed_project(workspace, problem)
    assert workspace.absolute(VENV_LINK).readlink() == VENV_TARGET


def test_a_new_attempt_never_overwrites_a_file(workspace, problem):
    workspace.write_text(f"{FOLDER}/bank/bank.py", "# mine\n")
    seed_project(workspace, problem)
    assert workspace.read_text(f"{FOLDER}/bank/bank.py") == "# mine\n"


def test_a_new_attempt_copies_only_what_the_folder_lacks(workspace, problem):
    workspace.write_text(f"{FOLDER}/bank/bank.py", "# mine\n")
    assert seed_project(workspace, problem).copied == ("README.md", "pyproject.toml")


def test_a_new_attempt_keeps_files_of_its_own(workspace, problem):
    workspace.write_text(f"{FOLDER}/bank/ledger.py", "# mine\n")
    seed_project(workspace, problem)
    assert workspace.exists(f"{FOLDER}/bank/ledger.py")


def test_a_working_link_is_kept(workspace, problem):
    seed_project(workspace, problem)
    workspace.write_text("python/.venv/bin/python", "#!/bin/sh\n")
    assert not seed_project(workspace, problem).linked


def test_a_typescript_folder_has_no_link(workspace, problem):
    meta = replace(problem.meta, languages=(Language.TYPESCRIPT,))
    seed_project(workspace, replace(problem, meta=meta))
    assert not os.path.lexists(workspace.absolute(VENV_LINK))


def go(problem: Problem) -> Problem:
    return replace(problem, meta=replace(problem.meta, languages=(Language.GO,)))


def test_a_go_folder_gets_a_go_work_of_its_own(workspace, problem):
    seed_project(workspace, go(problem))
    assert workspace.read_text(GO_WORK) == "go 1.24\n\nuse .\n"


def test_writing_the_go_work_links_the_go_folder(workspace, problem):
    assert seed_project(workspace, go(problem)).linked


def test_a_go_work_of_yours_is_kept(workspace, problem):
    workspace.write_text(GO_WORK, "go 1.25\n\nuse (\n\t.\n\t../shared\n)\n")
    seeded = seed_project(workspace, go(problem))
    assert (seeded.linked, workspace.read_text(GO_WORK).startswith("go 1.25")) == (False, True)


def test_a_python_folder_gets_no_go_work(workspace, problem):
    seed_project(workspace, problem)
    assert not workspace.exists(GO_WORK)


def test_a_resumed_go_attempt_writes_a_missing_go_work(workspace, problem):
    seed_project(workspace, go(problem))
    workspace.absolute(GO_WORK).unlink()
    resume_project(workspace, go(problem))
    assert workspace.exists(GO_WORK)


def test_archiving_leaves_the_go_work_behind(workspace, problem):
    seed_project(workspace, go(problem))
    archive_project(workspace, owner())
    assert not workspace.exists(f"{ARCHIVE}/go.work")


def test_the_pilot_starter_is_copied_whole(workspace, tmp_path):
    problems = tmp_path / "problems"
    shutil.copytree(CATALOG_PROBLEMS / PILOT, problems / PILOT)
    content = repository_root(tmp_path / "content", problems)
    seed_project(workspace, FsProblemRepository(content).load(SLUG))
    starter = CATALOG_PROBLEMS / PILOT / "starter"
    expected = {path.relative_to(starter).as_posix() for path in starter.rglob("*")}
    assert files_in(workspace, FOLDER) == {path for path in expected if (starter / path).is_file()}


def test_a_starter_file_that_is_not_text_is_a_content_error(workspace, problem):
    binary = ProjectTree((ProjectFile("bank/data.bin", 3, None),))
    with pytest.raises(ContentError, match=r"bank/data\.bin"):
        seed_project(workspace, replace(problem, project_files=ProjectFiles(binary)))


def test_a_starter_that_is_not_text_writes_nothing(workspace, problem):
    readme = ProjectFile("README.md", 7, "# Bank\n")
    binary = ProjectTree((readme, ProjectFile("bank/data.bin", 3, None)))
    with pytest.raises(ContentError):
        seed_project(workspace, replace(problem, project_files=ProjectFiles(binary)))
    assert not workspace.exists(FOLDER)


def test_a_project_problem_without_a_starter_is_a_content_error(workspace, problem):
    with pytest.raises(ContentError, match="starter"):
        seed_project(workspace, replace(problem, project_files=ProjectFiles(None)))


# a resumed attempt


def test_a_resumed_attempt_copies_the_starter_into_a_missing_folder(workspace, problem):
    resume_project(workspace, problem)
    assert files_in(workspace, FOLDER) == set(STARTER)


def test_a_resumed_attempt_never_restores_a_deleted_file(workspace, problem):
    seed_project(workspace, problem)
    workspace.absolute(f"{FOLDER}/README.md").unlink()
    resume_project(workspace, problem)
    assert not workspace.exists(f"{FOLDER}/README.md")


def test_a_resumed_attempt_copies_nothing_into_an_existing_folder(workspace, problem):
    seed_project(workspace, problem)
    assert resume_project(workspace, problem).copied == ()


def test_a_resumed_attempt_recreates_a_missing_link(workspace, problem):
    seed_project(workspace, problem)
    workspace.absolute(VENV_LINK).unlink()
    resume_project(workspace, problem)
    assert workspace.absolute(VENV_LINK).readlink() == VENV_TARGET


def test_a_resumed_attempt_recreates_a_dangling_link(workspace, problem):
    workspace.write_text(f"{FOLDER}/README.md", "# Bank\n")
    workspace.absolute(VENV_LINK).symlink_to("/moved/python/.venv")
    resume_project(workspace, problem)
    assert workspace.absolute(VENV_LINK).readlink() == VENV_TARGET


# a Rust folder's vendored source

RUST_FOLDER = "projects/bank-project-rust"
CARGO_CONFIG = f"{RUST_FOLDER}/.cargo/config.toml"
VENDORED_SOURCE = """\
[source.crates-io]
replace-with = "cstudy-vendor"

[source.cstudy-vendor]
directory = "../../.cs/runtime/runners/rust/vendor"
"""


@pytest.fixture(scope="module")
def rust_problem(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("content"), RUST_PROJECT_PROBLEMS)
    return FsProblemRepository(root).load("bank-project-rust")


def without_cargo_config(problem: Problem) -> Problem:
    files = problem.project_files or ProjectFiles(None)
    assert files.starter is not None
    kept = tuple(file for file in files.starter.files if file.path != ".cargo/config.toml")
    return replace(problem, project_files=replace(files, starter=ProjectTree(kept)))


def test_a_rust_folder_points_crates_io_at_the_vendored_crates(workspace, rust_problem):
    seed_project(workspace, rust_problem)
    assert workspace.read_text(CARGO_CONFIG) == VENDORED_SOURCE


def test_a_rust_folder_whose_starter_holds_the_config_needs_no_link(workspace, rust_problem):
    assert not seed_project(workspace, rust_problem).linked


def test_a_rust_starter_without_the_config_gets_it_written(workspace, rust_problem):
    seeded = seed_project(workspace, without_cargo_config(rust_problem))
    assert (seeded.linked, workspace.read_text(CARGO_CONFIG)) == (True, VENDORED_SOURCE)


def test_a_resumed_rust_attempt_writes_a_deleted_config_back(workspace, rust_problem):
    seed_project(workspace, rust_problem)
    workspace.absolute(CARGO_CONFIG).unlink()
    assert resume_project(workspace, rust_problem).linked


def test_a_resumed_rust_attempt_keeps_an_edited_config(workspace, rust_problem):
    seed_project(workspace, rust_problem)
    workspace.write_text(CARGO_CONFIG, "# mine\n")
    resume_project(workspace, rust_problem)
    assert workspace.read_text(CARGO_CONFIG) == "# mine\n"


def test_a_python_folder_gets_no_cargo_config(workspace, problem):
    seed_project(workspace, problem)
    assert not workspace.exists(f"{FOLDER}/.cargo/config.toml")


# --fresh and review attempts


def test_archiving_moves_the_folder_to_the_owner_archive(workspace, problem):
    seed_project(workspace, problem)
    archive_project(workspace, owner())
    assert files_in(workspace, ARCHIVE) == set(STARTER)


def test_archiving_returns_the_archive_directory(workspace, problem):
    seed_project(workspace, problem)
    assert archive_project(workspace, owner()) == ARCHIVE


def test_archiving_leaves_the_venv_link_behind(workspace, problem):
    seed_project(workspace, problem)
    archive_project(workspace, owner())
    assert not os.path.lexists(workspace.absolute(f"{ARCHIVE}/.venv"))


def test_archiving_without_a_folder_archives_nothing(workspace):
    assert archive_project(workspace, owner()) is None


def test_archiving_refuses_to_overwrite_an_archived_attempt(workspace, problem):
    seed_project(workspace, problem)
    workspace.write_text(f"{ARCHIVE}/README.md", "# an earlier attempt\n")
    with pytest.raises(UsageError, match=rf"{ARCHIVE} already exists"):
        archive_project(workspace, owner())


def test_a_refused_archive_keeps_the_folder(workspace, problem):
    seed_project(workspace, problem)
    workspace.write_text(f"{ARCHIVE}/README.md", "# an earlier attempt\n")
    with pytest.raises(UsageError):
        archive_project(workspace, owner())
    assert files_in(workspace, FOLDER) == set(STARTER)


def test_seeding_after_archiving_starts_from_the_starter_again(workspace, problem):
    seed_project(workspace, problem)
    workspace.write_text(f"{FOLDER}/bank/bank.py", "# my first try\n")
    archive_project(workspace, owner())
    seed_project(workspace, problem)
    assert workspace.read_text(f"{FOLDER}/bank/bank.py") == starter_text(problem, "bank/bank.py")
