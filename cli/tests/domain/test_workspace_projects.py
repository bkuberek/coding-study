"""Project folders in the workspace (docs/specs/installation-and-workspaces.md#project-folders)."""

from dataclasses import replace

import pytest

from coding_study.domain.problem import (
    ComparatorSpec,
    ComparatorType,
    ContentStatus,
    Difficulty,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.project import Project
from coding_study.domain.signature import ClassSignature
from coding_study.domain.workspace_projects import (
    ToolchainLink,
    folder_language,
    is_untracked,
    project_folder,
    project_slug,
    toolchain_link,
)

BANK = "projects/bank-project-python"
META = ProblemMeta(
    id="0249",
    slug="bank-project-python",
    title="Bank Project (Python)",
    status=ContentStatus.DRAFT,
    difficulty=Difficulty.HARD,
    track=Track.PRACTICAL,
    kind=ProblemKind.PROJECT,
    signature=ClassSignature("Bank", (), ()),
    comparator=ComparatorSpec(ComparatorType.OPS),
    approaches=(),
    languages=(Language.PYTHON,),
    project=Project("bank.bank"),
)


def test_a_project_folder_is_named_after_its_slug():
    assert project_folder("bank-project-python") == BANK


@pytest.mark.parametrize("language", [Language.PYTHON, Language.TYPESCRIPT])
def test_a_folder_is_written_in_its_problem_language(language):
    assert folder_language(replace(META, languages=(language,))) is language


def test_a_problem_of_another_kind_has_no_folder():
    assert folder_language(replace(META, kind=ProblemKind.PROGRESSIVE, project=None)) is None


def test_a_python_folder_links_to_the_workspace_venv():
    assert toolchain_link(Language.PYTHON) == ToolchainLink(".venv", "../../python/.venv")


@pytest.mark.parametrize(
    "language", [Language.TYPESCRIPT, Language.JAVA, Language.KOTLIN, Language.GO, Language.RUST]
)
def test_other_folders_need_no_link(language):
    assert toolchain_link(language) is None


# untracked entries


@pytest.mark.parametrize(
    "path",
    [
        ".venv",
        ".venv/bin/python",
        "node_modules",
        "node_modules/typescript/index.js",
        "__pycache__/bank.cpython-313.pyc",
        "bank/__pycache__/bank.cpython-313.pyc",
        ".pytest_cache/v/cache/lastfailed",
        ".ruff_cache/CACHEDIR.TAG",
        "tests/.ruff_cache/CACHEDIR.TAG",
        "uv.lock",
    ],
)
def test_the_venv_link_node_modules_caches_and_the_uv_lock_are_untracked(path):
    assert is_untracked(path)


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "pyproject.toml",
        "bank/bank.py",
        "tests/test_level_1.py",
        "venv/notes.md",
        ".venvs/notes.md",
        "bank/node_modules_helper.py",
        "pycache.py",
        "docs/uv.lock",
    ],
)
def test_everything_else_is_tracked(path):
    assert not is_untracked(path)


# file targets


@pytest.mark.parametrize(
    "path",
    [
        f"{BANK}/bank/bank.py",
        f"{BANK}/bank/ledger/entries.py",
        f"{BANK}/README.md",
        f"{BANK}/pyproject.toml",
        f"{BANK}/uv.lock",
    ],
)
def test_any_file_in_a_project_folder_names_the_folder(path):
    assert project_slug(path) == "bank-project-python"


@pytest.mark.parametrize(
    "path",
    [
        "",
        "projects",
        "projects/README.md",
        BANK,
        f"{BANK}/.venv/lib/python3.13/site-packages/pytest/__init__.py",
        f"{BANK}/node_modules/typescript/index.js",
        f"{BANK}/bank/__pycache__/bank.cpython-313.pyc",
        f"{BANK}/.pytest_cache/v/cache/lastfailed",
        f"{BANK}/.ruff_cache/CACHEDIR.TAG",
        "python/practice/two_sum.py",
        "notes/projects/bank-project-python/plan.md",
        "projectsx/bank-project-python/bank/bank.py",
    ],
)
def test_a_path_outside_a_folder_or_under_its_venv_or_caches_names_no_project(path):
    assert project_slug(path) is None
