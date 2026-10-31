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
    GO_VENDORED_MODULES,
    GoModuleFile,
    GoProjectFolder,
    ToolchainFile,
    ToolchainLink,
    folder_language,
    go_folder_problems,
    go_module_file,
    go_vendored_replacement,
    is_untracked,
    project_folder,
    project_slug,
    toolchain_files,
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


def test_a_go_folder_gets_a_go_work_file_of_its_own():
    assert toolchain_files(Language.GO) == (ToolchainFile("go.work", "go 1.24\n\nuse .\n"),)


@pytest.mark.parametrize("language", [Language.PYTHON, Language.TYPESCRIPT])
def test_other_folders_get_no_toolchain_file(language):
    assert toolchain_files(language) == ()


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
        "go.work",
        "go.work.sum",
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
        "go.mod",
        "tools/go.work",
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


# Go modules

STARTER_MODULE = """module bank-project-go

go 1.24

require github.com/shopspring/decimal v1.5.0

replace github.com/shopspring/decimal => {}
""".format("../../.cs/runtime/runners/go/third_party/github.com/shopspring/decimal")


def test_a_go_module_file_names_its_module_and_go_version():
    found = go_module_file(STARTER_MODULE)
    assert (found.module, found.go) == ("bank-project-go", "1.24")


def test_a_go_module_file_lists_its_requirements():
    assert go_module_file(STARTER_MODULE).requires == {"github.com/shopspring/decimal": "v1.5.0"}


def test_a_go_module_file_lists_its_replacements():
    assert go_module_file(STARTER_MODULE).replaces == {
        "github.com/shopspring/decimal": go_vendored_replacement("github.com/shopspring/decimal")
    }


def test_a_go_module_file_reads_blocks_and_ignores_comments():
    text = """// The bank.
module bank // the module
go 1.24
require (
\texample.com/a v1.0.0 // indirect
\texample.com/b v2.1.0
)
replace (
\texample.com/a => ./a
\texample.com/b v2.1.0 => example.com/c v2.2.0
)
"""
    assert go_module_file(text) == GoModuleFile(
        module="bank",
        go="1.24",
        requires={"example.com/a": "v1.0.0", "example.com/b": "v2.1.0"},
        replaces={"example.com/a": "./a", "example.com/b": "example.com/c v2.2.0"},
    )


def test_a_go_module_file_without_lines_names_nothing():
    assert go_module_file("") == GoModuleFile(None, None, {}, {})


def test_the_vendored_decimal_module_is_replaced_by_the_runtimes_copy():
    assert go_vendored_replacement("github.com/shopspring/decimal") == (
        "../../.cs/runtime/runners/go/third_party/github.com/shopspring/decimal"
    )


def test_decimal_is_the_vendored_go_module():
    assert GO_VENDORED_MODULES == {"github.com/shopspring/decimal": "v1.5.0"}


def go_folder(slug: str, module: str | None = None, **changes) -> GoProjectFolder:
    found = GoProjectFolder(f"projects/{slug}", module or slug, has_work_file=True)
    return replace(found, **changes)


def test_go_folders_with_work_files_and_their_own_modules_have_no_problem():
    assert go_folder_problems([go_folder("a-project-go"), go_folder("b-project-go")]) == ()


def test_a_go_folder_without_its_work_file_is_a_problem():
    folder = go_folder("a-project-go", has_work_file=False)
    assert go_folder_problems([folder]) == ("projects/a-project-go has no go.work",)


def test_a_replacement_that_does_not_resolve_is_a_problem():
    folder = go_folder("a-project-go", unresolved=("../../gone",))
    assert go_folder_problems([folder]) == (
        "projects/a-project-go/go.mod replaces a module with ../../gone, which does not exist",
    )


def test_two_go_folders_with_one_module_path_are_a_problem():
    folders = [go_folder("a-project-go", "bank"), go_folder("b-project-go", "bank")]
    assert go_folder_problems(folders) == (
        "projects/a-project-go and projects/b-project-go both declare module bank",
    )


def test_a_go_folder_without_a_module_line_shares_no_module():
    folders = [go_folder("a-project-go", has_work_file=True), replace(go_folder("b"), module=None)]
    assert go_folder_problems(folders) == ()


def test_three_go_folders_with_one_module_path_are_one_problem():
    folders = [go_folder(slug, "bank") for slug in ("a", "b", "c")]
    assert go_folder_problems(folders) == (
        "projects/a, projects/b and projects/c all declare module bank",
    )
