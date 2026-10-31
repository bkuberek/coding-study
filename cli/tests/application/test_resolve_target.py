import shutil
from pathlib import Path

import pytest

from coding_study.application.resolve_target import Target, resolve_target
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.fakes import make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
KOTLIN_TWO_SUM = "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt"
JAVA_LRU_CACHE = "jvm/java/src/main/java/practice/lru_cache/LRUCache.java"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return copy_repository(tmp_path / "ws", PRACTICE)


@pytest.fixture
def environment(workspace: Path):
    return make_environment(workspace)


def resolve(
    environment, text: str | None, language: Language | None = None, cwd: Path | None = None
):
    return resolve_target(environment, Target(text, language), cwd or environment.root)


@pytest.mark.parametrize(
    ("path", "language"),
    [
        ("python/practice/two_sum.py", Language.PYTHON),
        ("typescript/practice/two-sum.ts", Language.TYPESCRIPT),
        (KOTLIN_TWO_SUM, Language.KOTLIN),
        ("jvm/java/src/main/java/practice/two_sum/Solution.java", Language.JAVA),
    ],
)
def test_a_relative_path_resolves_the_problem_and_the_language(environment, path, language):
    assert resolve(environment, path) == Target("two-sum", language)


def test_an_absolute_path_resolves_like_a_relative_one(environment):
    absolute = str(environment.root / KOTLIN_TWO_SUM)
    assert resolve(environment, absolute) == Target("two-sum", Language.KOTLIN)


def test_a_class_design_jvm_file_is_named_after_the_declared_class(environment):
    assert resolve(environment, JAVA_LRU_CACHE) == Target("lru-cache", Language.JAVA)


def test_an_underscore_name_maps_back_to_its_hyphenated_slug(environment):
    assert resolve(environment, "python/practice/lru_cache.py").slug == "lru-cache"


def test_a_relative_path_resolves_against_the_working_directory(environment):
    cwd = environment.root / "python" / "practice"
    assert resolve(environment, "two_sum.py", cwd=cwd) == Target("two-sum", Language.PYTHON)


def test_dot_segments_are_normalized(environment):
    cwd = environment.root / "jvm"
    assert resolve(environment, "../python/./practice/two_sum.py", cwd=cwd).slug == "two-sum"


def test_a_symlinked_workspace_root_still_contains_its_files(environment, tmp_path):
    link = tmp_path / "link"
    link.symlink_to(environment.root, target_is_directory=True)
    assert resolve(environment, str(link / "python/practice/two_sum.py")).slug == "two-sum"


def test_a_matching_language_option_is_accepted(environment):
    target = resolve(environment, "python/practice/two_sum.py", Language.PYTHON)
    assert target == Target("two-sum", Language.PYTHON)


def test_a_disagreeing_language_option_is_a_usage_error_naming_both(environment):
    with pytest.raises(UsageError, match=r"python.*kotlin|kotlin.*python"):
        resolve(environment, "python/practice/two_sum.py", Language.KOTLIN)


def test_a_path_outside_the_workspace_is_a_usage_error(environment, tmp_path):
    outside = tmp_path / "elsewhere" / "python" / "practice" / "two_sum.py"
    with pytest.raises(UsageError, match="not a solution file in this workspace"):
        resolve(environment, str(outside))


def test_the_error_names_the_offending_path(environment):
    with pytest.raises(UsageError, match=r"not a solution file in this workspace: notes/a\.py"):
        resolve(environment, "notes/a.py")


def test_a_workspace_file_outside_the_layout_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="not a solution file in this workspace"):
        resolve(environment, "python/practice/nested/two_sum.py")


def test_a_layout_path_without_a_problem_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="no problem"):
        resolve(environment, "python/practice/missing_problem.py")


@pytest.mark.parametrize("text", ["two-sum", "0001", None])
def test_a_slug_an_id_or_nothing_is_left_as_it_is(environment, text):
    assert resolve(environment, text, Language.JAVA) == Target(text, Language.JAVA)


def test_a_slug_stays_a_slug_when_a_file_of_that_name_exists(environment):
    (environment.root / "two-sum").write_text("not a solution")
    assert resolve(environment, "two-sum") == Target("two-sum", None)


@pytest.fixture
def practice_directory(environment) -> str:
    directory = "python/practice"
    (environment.root / directory).mkdir(parents=True)
    return directory


def test_the_workspace_root_asks_for_a_solution_file_in_the_editor(environment):
    with pytest.raises(UsageError, match=r"open a solution file in the editor first \(got a"):
        resolve(environment, f"{environment.root}/.")


def test_a_directory_asks_for_a_solution_file_in_the_editor(environment, practice_directory):
    absolute = str(environment.root / practice_directory)
    with pytest.raises(UsageError, match=r"open a solution file in the editor first \(got a"):
        resolve(environment, absolute)


def test_the_directory_message_names_the_directory(environment, practice_directory):
    with pytest.raises(UsageError, match=r"got a directory: python/practice\)"):
        resolve(environment, practice_directory)


# project folders: projects/<slug>/


BANK_FOLDER = "projects/bank-project-python"


@pytest.fixture
def projects(workspace: Path):
    shutil.copytree(PROJECT_PROBLEMS / BANK_PROJECT, workspace / "problems" / BANK_PROJECT)
    (workspace / BANK_FOLDER / "bank").mkdir(parents=True)
    return make_environment(workspace)


@pytest.mark.parametrize(
    "path",
    [
        f"{BANK_FOLDER}/bank/bank.py",
        f"{BANK_FOLDER}/bank/ledger/entries.py",
        f"{BANK_FOLDER}/tests/test_level_1.py",
        f"{BANK_FOLDER}/README.md",
        f"{BANK_FOLDER}/pyproject.toml",
    ],
)
def test_any_file_in_a_project_folder_is_its_problem_in_its_language(projects, path):
    assert resolve(projects, path) == Target("bank-project-python", Language.PYTHON)


def test_an_absolute_project_path_resolves_like_a_relative_one(projects):
    absolute = str(projects.root / BANK_FOLDER / "bank" / "bank.py")
    assert resolve(projects, absolute) == Target("bank-project-python", Language.PYTHON)


def test_a_project_file_resolves_against_the_working_directory(projects):
    cwd = projects.root / BANK_FOLDER / "bank"
    assert resolve(projects, "bank.py", cwd=cwd) == Target("bank-project-python", Language.PYTHON)


def test_the_language_option_may_repeat_the_project_language(projects):
    target = resolve(projects, f"{BANK_FOLDER}/bank/bank.py", Language.PYTHON)
    assert target == Target("bank-project-python", Language.PYTHON)


def test_another_language_option_is_a_usage_error_naming_both(projects):
    with pytest.raises(UsageError, match=r"python.*typescript|typescript.*python"):
        resolve(projects, f"{BANK_FOLDER}/bank/bank.py", Language.TYPESCRIPT)


def test_the_project_folder_itself_asks_for_a_solution_file_in_the_editor(projects):
    with pytest.raises(UsageError, match=r"got a directory: projects/bank-project-python\)"):
        resolve(projects, BANK_FOLDER)


@pytest.mark.parametrize(
    "inside",
    [
        ".venv/lib/python3.13/site-packages/pytest/__init__.py",
        "node_modules/typescript/index.js",
        "bank/__pycache__/bank.cpython-313.pyc",
        ".pytest_cache/v/cache/lastfailed",
    ],
)
def test_a_file_under_the_venv_node_modules_or_caches_is_not_a_solution_file(projects, inside):
    with pytest.raises(UsageError, match="not a solution file in this workspace"):
        resolve(projects, f"{BANK_FOLDER}/{inside}")


def test_a_file_reached_through_the_venv_link_is_not_a_solution_file(projects):
    (projects.root / "python" / ".venv" / "lib").mkdir(parents=True)
    (projects.root / BANK_FOLDER / ".venv").symlink_to("../../python/.venv")
    with pytest.raises(UsageError, match="not a solution file in this workspace"):
        resolve(projects, f"{BANK_FOLDER}/.venv/lib/site.py")


def test_a_file_directly_in_projects_is_not_a_solution_file(projects):
    with pytest.raises(UsageError, match="not a solution file in this workspace"):
        resolve(projects, "projects/README.md")


def test_a_folder_named_after_no_problem_is_a_usage_error(projects):
    with pytest.raises(UsageError, match=r"no problem for projects/ledger/bank\.py"):
        resolve(projects, "projects/ledger/bank.py")


def test_a_folder_named_after_a_problem_of_another_kind_is_a_usage_error(projects):
    with pytest.raises(UsageError, match="two-sum is not a project problem"):
        resolve(projects, "projects/two-sum/solution.py")
