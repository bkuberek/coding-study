"""The programs of the languages, looked up as the runners start them
(docs/specs/cli.md#cstudy-verify)."""

import stat
from pathlib import Path

import pytest

from coding_study.adapters.path_toolchain_check import PathToolchainCheck
from coding_study.domain.layout import PYTHON_INTERPRETER, PYTHON_PROJECT
from coding_study.domain.problem import Language


def program(directory: Path, name: str) -> None:
    path = directory / name
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def bin_directory(tmp_path):
    directory = tmp_path / "bin"
    directory.mkdir()
    return directory


def check(bin_directory: Path, workspace: Path) -> PathToolchainCheck:
    return PathToolchainCheck({"PATH": str(bin_directory)}, workspace)


@pytest.mark.parametrize(
    ("language", "name"),
    [(Language.TYPESCRIPT, "node"), (Language.GO, "go"), (Language.RUST, "cargo")],
)
def test_a_program_that_is_not_on_path_is_missing(bin_directory, tmp_path, language, name):
    assert check(bin_directory, tmp_path).missing(language) == f"{name} was not found on PATH"


@pytest.mark.parametrize(
    ("language", "name"),
    [(Language.TYPESCRIPT, "node"), (Language.GO, "go"), (Language.RUST, "cargo")],
)
def test_a_program_on_path_is_not_missing(bin_directory, tmp_path, language, name):
    program(bin_directory, name)
    assert check(bin_directory, tmp_path).missing(language) is None


def test_the_path_of_the_environment_is_searched_not_the_process_path(
    bin_directory, tmp_path, monkeypatch
):
    other = tmp_path / "other"
    other.mkdir()
    program(other, "cargo")
    monkeypatch.setenv("PATH", str(other))
    assert check(bin_directory, tmp_path).missing(Language.RUST) is not None


def test_java_and_kotlin_are_the_jdks_not_this_checks(bin_directory, tmp_path):
    subject = check(bin_directory, tmp_path)
    assert (subject.missing(Language.JAVA), subject.missing(Language.KOTLIN)) == (None, None)


def test_python_needs_the_interpreter_of_the_workspace(bin_directory, tmp_path):
    reason = check(bin_directory, tmp_path).missing(Language.PYTHON)
    assert reason == f"{PYTHON_PROJECT}/{PYTHON_INTERPRETER} is missing; run `cstudy doctor --fix`"


def test_python_is_there_with_its_interpreter(bin_directory, tmp_path):
    interpreter = tmp_path / PYTHON_PROJECT / PYTHON_INTERPRETER
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("")
    assert check(bin_directory, tmp_path).missing(Language.PYTHON) is None
