"""Starter helpers: `cstudy start` appends a problem's `helpers/` file for the language to the
generated starter, and `cstudy verify` builds the stub with it (D1) and checks where helpers may
be (S8). Python runs for real through the mini runner."""

from pathlib import Path

import pytest

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.fakes import repository_root

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
PROBLEM = "problems/0001-two-sum"
DEBUGGING = Path(__file__).resolve().parents[1] / "fixtures" / "debugging" / "problems"
HELPER = 'def digest(data: bytes) -> str:\n    """Hexadecimal."""\n    return data.hex()\n'


@pytest.fixture
def environment(tmp_path):
    return e2e_environment(repository_root(tmp_path, PRACTICE))


def add_helper(environment, name: str, text: str = HELPER, problem: str = PROBLEM) -> None:
    folder = environment.root / problem / "helpers"
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(text)


def verify(environment, slug: str = "two-sum", **fields):
    request = VerifyRequest(**{"language": Language.PYTHON, "slugs": (slug,), **fields})
    return verify_content(environment, request, lambda _line: None).problems[0]


def test_start_appends_the_helper_to_the_generated_starter(environment):
    add_helper(environment, "digest.py")
    start_attempt(environment, StartRequest("two-sum"))
    stub = environment.workspace.read_text("python/practice/two_sum.py")
    assert stub.endswith("raise NotImplementedError\n\n\n" + HELPER)
    assert "def two_sum(" in stub


def test_a_problem_with_a_helper_verifies(environment):
    add_helper(environment, "digest.py")
    assert verify(environment).passed


def test_the_stub_check_builds_the_stub_with_its_helper(environment):
    add_helper(environment, "digest.py", "def digest(:\n")
    problem = verify(environment).languages[0].problems[0]
    assert problem.startswith("stub does not load: SyntaxError")


def test_a_helper_of_no_language_is_a_static_error(environment):
    add_helper(environment, "notes.txt", "Not code.\n")
    assert verify(environment, static_only=True).static_errors == (
        f"{PROBLEM}/helpers/notes.txt: maps to no language in languages",
    )


def test_two_helpers_for_one_language_are_a_static_error(environment):
    add_helper(environment, "a.py")
    add_helper(environment, "b.py")
    assert verify(environment, static_only=True).static_errors == (
        f"{PROBLEM}/helpers/b.py: a second helper for python; a language has at most one",
    )


def test_a_buggy_stub_takes_no_helper(tmp_path):
    environment = e2e_environment(repository_root(tmp_path, DEBUGGING))
    problem = "problems/0001-running-max"
    add_helper(environment, "digest.py", problem=problem)
    assert verify(environment, "running-max", static_only=True).static_errors == (
        f"{problem}/helpers: present but stub is buggy",
    )
