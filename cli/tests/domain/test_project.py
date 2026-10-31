"""The `project` block of meta.yaml and the paths inside a project folder."""

import re

import pytest

from coding_study.domain.problem import Language
from coding_study.domain.project import (
    DEFAULT_TESTS_DIRECTORY,
    PROJECT_LANGUAGES,
    Project,
    ProjectFile,
    ProjectTree,
    entry_files,
    entry_issue,
    level_test_file,
    relative_path_issue,
)

WITHOUT_PROJECTS = (Language.JAVA, Language.KOTLIN, Language.GO, Language.RUST)


def test_project_problems_exist_in_python_and_typescript():
    assert PROJECT_LANGUAGES == (Language.PYTHON, Language.TYPESCRIPT)


def test_generated_tests_go_to_tests_by_default():
    assert Project("bank.bank").tests == DEFAULT_TESTS_DIRECTORY == "tests"


# relative paths


@pytest.mark.parametrize(
    "path", ["README.md", "bank/bank.py", "src/bank.ts", ".vscode/settings.json", "a..b/c"]
)
def test_a_path_inside_its_folder_is_valid(path):
    assert relative_path_issue(path) is None


@pytest.mark.parametrize(
    ("path", "issue"),
    [
        ("", "is empty"),
        ("/etc/passwd", "is absolute"),
        ("../bank.py", 'leaves its folder through ".."'),
        ("bank/../../bank.py", 'leaves its folder through ".."'),
        ("bank/..", 'leaves its folder through ".."'),
        ("bank//bank.py", 'has an empty or "." segment'),
        ("./bank.py", 'has an empty or "." segment'),
        ("bank/", 'has an empty or "." segment'),
        ("bank\\bank.py", "uses \\ instead of /"),
    ],
    ids=["empty", "absolute", "up", "up twice", "up at the end", "empty", "dot", "trailing", "\\"],
)
def test_a_path_that_could_leave_its_folder_is_rejected(path, issue):
    assert relative_path_issue(path) == issue


# entry


@pytest.mark.parametrize("entry", ["bank", "bank.bank", "bank_app.core.bank", "_bank", "bank.py"])
def test_a_python_entry_is_a_dotted_module(entry):
    assert entry_issue(entry, Language.PYTHON) is None


@pytest.mark.parametrize(
    "entry", ["bank/bank", "bank..bank", ".bank", "bank.", "1bank", "bank.class", "bank-app", ""]
)
def test_a_python_entry_that_is_not_a_dotted_module_is_rejected(entry):
    assert entry_issue(entry, Language.PYTHON) == (
        f'"{entry}" is not a dotted module name such as bank.bank'
    )


@pytest.mark.parametrize("entry", ["src/bank.ts", "bank.ts"])
def test_a_typescript_entry_is_a_ts_file(entry):
    assert entry_issue(entry, Language.TYPESCRIPT) is None


@pytest.mark.parametrize(
    "entry", ["src/bank.js", "src/bank", "/src/bank.ts", "../bank.ts", "src//bank.ts", "bank.bank"]
)
def test_a_typescript_entry_that_is_not_a_ts_file_in_the_project_is_rejected(entry):
    assert entry_issue(entry, Language.TYPESCRIPT) == (
        f'"{entry}" is not a .ts file inside the project such as src/bank.ts'
    )


def test_a_python_entry_is_a_module_file_or_a_package():
    assert entry_files("bank.bank", Language.PYTHON) == ("bank/bank.py", "bank/bank/__init__.py")


def test_a_typescript_entry_is_its_own_file():
    assert entry_files("src/bank.ts", Language.TYPESCRIPT) == ("src/bank.ts",)


# generated tests


@pytest.mark.parametrize(
    ("language", "expected"),
    [(Language.PYTHON, "tests/test_level_2.py"), (Language.TYPESCRIPT, "tests/level-2.test.ts")],
)
def test_each_level_has_one_generated_test_file(language, expected):
    assert level_test_file(Project("bank.bank"), language, 2) == expected


def test_generated_test_files_go_to_the_project_tests_directory():
    project = Project("bank.bank", "checks/levels")
    assert level_test_file(project, Language.PYTHON, 1) == "checks/levels/test_level_1.py"


@pytest.mark.parametrize(
    "use",
    [
        lambda language: entry_issue("bank.bank", language),
        lambda language: entry_files("bank.bank", language),
        lambda language: level_test_file(Project("bank.bank"), language, 1),
    ],
    ids=["entry_issue", "entry_files", "level_test_file"],
)
@pytest.mark.parametrize("language", WITHOUT_PROJECTS)
def test_other_languages_have_no_project_problems_yet(use, language):
    with pytest.raises(ValueError, match=f"project problems are not yet supported in {language}"):
        use(language)


# file trees


@pytest.mark.parametrize("path", ["/etc/passwd", "../outside.py", "bank/../../outside.py"])
def test_a_project_file_never_lies_outside_its_folder(path):
    with pytest.raises(ValueError, match=re.escape(f'project file "{path}"')):
        ProjectFile(path, 0, "")


def test_a_tree_knows_its_paths():
    tree = ProjectTree((ProjectFile("README.md", 3, "Hi\n"), ProjectFile("bank/bank.py", 0, "")))
    assert tree.paths == frozenset({"README.md", "bank/bank.py"})


def test_a_tree_size_is_the_size_of_its_files():
    tree = ProjectTree((ProjectFile("README.md", 3, "Hi\n"), ProjectFile("logo.png", 70, None)))
    assert tree.size == 73


def test_a_file_finds_a_file_of_its_tree_by_path():
    readme = ProjectFile("README.md", 3, "Hi\n")
    assert ProjectTree((readme,)).file("README.md") == readme


def test_a_tree_has_no_file_at_a_missing_path():
    assert ProjectTree(()).file("README.md") is None
