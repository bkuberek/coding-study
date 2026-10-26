import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.git_changed_files import GitChangedFiles
from coding_study.domain.errors import VersionControlError

ISOLATED_GIT = ("-c", "user.name=test", "-c", "user.email=test@example.com")
ISOLATED_GIT += ("-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null")


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *ISOLATED_GIT, *arguments], cwd=repository, check=True, capture_output=True
    )


def write(repository: Path, path: str, text: str = "x\n") -> None:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository whose main branch holds two problems, checked out on a feature branch."""
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, ".gitignore", "*.log\n")
    write(tmp_path, "problems/0001-two-sum/meta.yaml")
    write(tmp_path, "problems/0002-lru-cache/meta.yaml")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "main")
    git(tmp_path, "switch", "-q", "-c", "feature")
    return tmp_path


def changed(root: Path) -> set[str]:
    return set(GitChangedFiles(root).changed_since("main"))


def test_nothing_changed(repository):
    assert changed(repository) == set()


def test_commits_on_the_branch_count(repository):
    write(repository, "problems/0003-word-break/meta.yaml")
    git(repository, "add", ".")
    git(repository, "commit", "-q", "-m", "add word-break")
    assert changed(repository) == {"problems/0003-word-break/meta.yaml"}


def test_unstaged_and_staged_edits_count(repository):
    write(repository, "problems/0001-two-sum/meta.yaml", "edited\n")
    write(repository, "problems/0002-lru-cache/meta.yaml", "staged\n")
    git(repository, "add", "problems/0002-lru-cache/meta.yaml")
    assert changed(repository) == {
        "problems/0001-two-sum/meta.yaml",
        "problems/0002-lru-cache/meta.yaml",
    }


def test_untracked_files_count_but_ignored_ones_do_not(repository):
    write(repository, "problems/0003-word-break/problem.md")
    write(repository, "problems/0003-word-break/run.log")
    assert changed(repository) == {"problems/0003-word-break/problem.md"}


def test_commits_on_main_after_the_branch_point_do_not_count(repository):
    git(repository, "switch", "-q", "main")
    write(repository, "problems/0002-lru-cache/meta.yaml", "on main\n")
    git(repository, "commit", "-q", "-am", "main moves on")
    git(repository, "switch", "-q", "feature")
    assert changed(repository) == set()


def test_paths_are_relative_to_a_root_below_the_repository(repository):
    write(repository, "content/problems/0001-x/meta.yaml")
    write(repository, "elsewhere.md")
    assert changed(repository / "content") == {"problems/0001-x/meta.yaml"}


def test_paths_with_spaces(repository):
    write(repository, "problems/0001-two-sum/my notes.md")
    assert changed(repository) == {"problems/0001-two-sum/my notes.md"}


def test_a_missing_base_branch_is_an_error(repository):
    with pytest.raises(VersionControlError, match="trunk"):
        GitChangedFiles(repository).changed_since("trunk")


def test_outside_a_repository_is_an_error(tmp_path):
    with pytest.raises(VersionControlError):
        GitChangedFiles(tmp_path).changed_since("main")


def test_a_missing_git_is_an_error(repository):
    with pytest.raises(VersionControlError, match="not found"):
        GitChangedFiles(repository, executable="no-such-git").changed_since("main")
