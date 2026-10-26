"""`stub: buggy` problems (debugging track): cstudy start hands out the buggy file, cstudy verify
proves it fails while the fixed references pass. Python runs for real through the mini runner."""

from pathlib import Path

import pytest

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.fakes import repository_root

DEBUGGING = Path(__file__).resolve().parents[1] / "fixtures" / "debugging" / "problems"
PROBLEM = "problems/0001-running-max"
BUGGY_PYTHON = DEBUGGING / "0001-running-max" / "buggy" / "solution.py"
JVM_STUBS = {
    Language.JAVA: "jvm/java/src/main/java/practice/running_max/Solution.java",
    Language.KOTLIN: "jvm/kotlin/src/main/kotlin/practice/running_max/Solution.kt",
}


@pytest.fixture
def environment(tmp_path):
    return e2e_environment(repository_root(tmp_path, DEBUGGING))


def verify(environment, **fields):
    request = VerifyRequest(**{"language": Language.PYTHON, "slugs": ("running-max",), **fields})
    return verify_content(environment, request, lambda _line: None).problems[0]


def replace_text(environment, relative: str, old: str, new: str) -> None:
    path = environment.root / PROBLEM / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_start_copies_the_buggy_file(environment):
    start_attempt(environment, StartRequest("running-max"))
    stub = environment.workspace.read_text("python/practice/running_max.py")
    assert stub == BUGGY_PYTHON.read_text()


@pytest.mark.parametrize(
    ("language", "package"),
    [
        (Language.JAVA, "package practice.running_max;\n\n// Running Maximum"),
        (Language.KOTLIN, "package practice.running_max\n\n// Running Maximum"),
    ],
)
def test_start_adds_the_package_on_the_jvm(environment, language, package):
    start_attempt(environment, StartRequest("running-max", language))
    assert environment.workspace.read_text(JVM_STUBS[language]).startswith(package)


def test_buggy_problem_verifies(environment):
    assert verify(environment, require_ready=True).passed


def test_buggy_file_that_passes_every_case_fails_verify(environment):
    replace_text(environment, "buggy/solution.py", "best = 0", "best = nums[0]")
    assert verify(environment).languages[0].problems == (
        "buggy stub passes every case; it must fail at least one",
    )


def test_buggy_file_that_does_not_load_fails_verify(environment):
    replace_text(environment, "buggy/solution.py", "def running_max", "def running_max(:")
    problem = verify(environment).languages[0].problems[0]
    assert problem.startswith("buggy stub does not load: SyntaxError")


def test_fixed_reference_must_still_pass(environment):
    replace_text(environment, "solutions/single-pass.py", "best = nums[0]", "best = 0")
    failures = verify(environment).languages[0].approaches[0].failures
    assert failures[0].startswith("ex2 FAIL: expected [-4, -4, -2], got [0, 0, 0]")


def test_missing_buggy_file_is_a_static_error(environment):
    (environment.root / PROBLEM / "buggy" / "solution.kt").unlink()
    assert verify(environment, static_only=True).static_errors == (
        f"{PROBLEM}/buggy/solution.kt: missing (stub: buggy)",
    )


def test_buggy_file_for_an_unlisted_language_is_a_static_error(environment):
    replace_text(environment, "meta.yaml", "stub: buggy\n", "stub: buggy\nlanguages: [python]\n")
    assert verify(environment, static_only=True).static_errors == tuple(
        f"{PROBLEM}/buggy/solution.{extension}: maps to no language in languages"
        for extension in ("java", "kt", "ts")
    )


def test_buggy_files_need_stub_buggy(environment):
    replace_text(environment, "meta.yaml", "stub: buggy\n", "")
    assert verify(environment, static_only=True).static_errors == (
        f"{PROBLEM}/buggy: present but stub is generated",
    )
