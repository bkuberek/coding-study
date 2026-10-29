"""`stub: buggy` with the real toolchains: the buggy file fails and the fixed reference passes in
Python, TypeScript, Java and Kotlin.

Marked `slow` (Node, the workspace venv and Gradle). The content root is temporary: copies of the
schemas and of the debugging fixture, plus a symlink to the real `runners/`; the workspace is the
session's practice workspace, where `cstudy verify` only builds under `.cs/build/`.
"""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.verify_content import (
    ProblemVerification,
    VerifyRequest,
    verify_content,
)
from coding_study.domain.problem import CORE_LANGUAGES
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY

pytestmark = pytest.mark.slow

DEBUGGING = Path(__file__).resolve().parents[1] / "fixtures" / "debugging" / "problems"
PROBLEM = "problems/0001-running-max"
EXTENSIONS = ("py", "ts", "java", "kt")


def repository(root: Path) -> Path:
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    shutil.copytree(DEBUGGING, root / "problems")
    (root / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return root


def verified(root: Path, workspace: Path) -> ProblemVerification:
    environ = {"CSTUDY_CONTENT": str(root), "CSTUDY_WORKSPACE": str(workspace)}
    environment = load_environment(root, environ, workspace)
    request = VerifyRequest(slugs=("running-max",), require_ready=True)
    return verify_content(environment, request, lambda _line: None).problems[0]


@pytest.fixture(scope="module")
def debugging(
    tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path
) -> ProblemVerification:
    root = repository(tmp_path_factory.mktemp("debugging-root"))
    return verified(root, practice_workspace)


@pytest.fixture(scope="module")
def without_bug(
    tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path
) -> ProblemVerification:
    """Every buggy file replaced by the fixed reference."""
    root = repository(tmp_path_factory.mktemp("fixed-root"))
    for extension in EXTENSIONS:
        fixed = root / PROBLEM / "solutions" / f"single-pass.{extension}"
        shutil.copyfile(fixed, root / PROBLEM / "buggy" / f"solution.{extension}")
    return verified(root, practice_workspace)


def test_every_language_is_verified(debugging):
    assert [result.language for result in debugging.languages] == list(CORE_LANGUAGES)


def test_buggy_files_fail_and_references_pass_in_every_language(debugging):
    assert debugging.passed, (debugging.languages, debugging.dynamic_errors)


def test_a_buggy_file_without_a_bug_fails_verify_in_every_language(without_bug):
    assert [result.problems for result in without_bug.languages] == [
        ("buggy stub passes every case; it must fail at least one",)
    ] * len(CORE_LANGUAGES)
