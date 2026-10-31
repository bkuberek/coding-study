"""`cstudy test` on a function problem whose code does not compile: each compiler's report is read
into diagnostics at the user's file (docs/specs/cli.md#diagnostics).

The runner is a fake that fails the build with the compiler lines the real toolchains reported
(tests/domain/recorded), so the wiring is tested without Gradle, Go or Cargo.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.ports import BuildFailed
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from tests.domain.recorded_output import recorded
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
    two_sum,
)

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
REPORTS = {
    Language.JAVA: "javac.txt",
    Language.KOTLIN: "kotlinc.txt",
    Language.GO: "go.txt",
    Language.RUST: "rustc.txt",
}
USER_FILES = {
    Language.JAVA: "jvm/java/src/main/java/practice/two_sum/Solution.java",
    Language.KOTLIN: "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
    Language.GO: "go/practice/two_sum/two_sum.go",
    Language.RUST: "rust/practice/two_sum.rs",
}
FIRST_PLACES = {
    Language.JAVA: (7, 21),
    Language.KOTLIN: (8, 24),
    Language.GO: (5, 2),
    Language.RUST: (2, 22),
}
COMPILED = tuple(REPORTS)


def diagnostics(tmp_path, monkeypatch, language: Language, lines: list[str]) -> list[dict]:
    """The `diagnostic` events of two-sum in `language` whose build fails with `lines`."""
    failing = FakeLanguageRunner(BuildFailed(tuple(lines)))
    toolchains = FakeToolchains(
        runners={Language.PYTHON: FakeLanguageRunner(), language: failing},
        stub_generators={language: FakeStubGenerator()},
    )
    environment = make_environment(
        repository_root(tmp_path, PRACTICE),
        toolchains=toolchains,
        runner_process=ScriptedRunnerProcess(two_sum),
    )
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum", language))
    result = runner.invoke(cli.app, ["test", "--events"])
    events = [json.loads(line) for line in result.stdout.splitlines()]
    return [event for event in events if event["type"] == "diagnostic"]


def recorded_lines(language: Language) -> list[str]:
    return recorded(REPORTS[language]).splitlines()


@pytest.mark.parametrize("language", COMPILED)
def test_the_first_error_is_at_its_line_and_column_of_the_users_file(
    tmp_path, monkeypatch, language
):
    first, *_ = diagnostics(tmp_path, monkeypatch, language, recorded_lines(language))
    assert (first["file"], first["line"], first["column"]) == (
        USER_FILES[language],
        *FIRST_PLACES[language],
    )


@pytest.mark.parametrize("language", COMPILED)
def test_every_error_of_the_report_is_a_build_diagnostic(tmp_path, monkeypatch, language):
    found = diagnostics(tmp_path, monkeypatch, language, recorded_lines(language))
    assert {event["source"] for event in found} == {"build"}


@pytest.mark.parametrize("language", COMPILED)
def test_every_diagnostic_with_a_file_names_the_users_file(tmp_path, monkeypatch, language):
    found = diagnostics(tmp_path, monkeypatch, language, recorded_lines(language))
    assert {event["file"] for event in found} <= {USER_FILES[language], None}


def test_a_report_with_several_errors_gives_a_diagnostic_for_each(tmp_path, monkeypatch):
    found = diagnostics(tmp_path, monkeypatch, Language.GO, recorded_lines(Language.GO))
    assert len(found) == 8


def test_a_compiler_message_is_without_the_place_it_was_read_from(tmp_path, monkeypatch):
    found = diagnostics(tmp_path, monkeypatch, Language.GO, recorded_lines(Language.GO))
    assert found[3]["message"] == "undefined: undefinedName"


def test_a_java_file_beside_the_users_is_the_problems(tmp_path, monkeypatch):
    line = "/ws/jvm/java/src/main/java/practice/two_sum/Helper.java:3: error: x"
    (found,) = diagnostics(tmp_path, monkeypatch, Language.JAVA, [line])
    assert found["file"] == "jvm/java/src/main/java/practice/two_sum/Helper.java"


def test_a_file_outside_the_problem_keeps_the_message_and_has_no_place(tmp_path, monkeypatch):
    line = "/ws/.cs/build/jvm/java/src/main/java/ref/two_sum/Other.java:3: error: broken"
    (found,) = diagnostics(tmp_path, monkeypatch, Language.JAVA, [line])
    assert (found["file"], found["line"], found["column"], found["message"]) == (
        None,
        None,
        None,
        "broken",
    )


def test_a_report_the_parser_does_not_know_is_a_diagnostic_for_each_line(tmp_path, monkeypatch):
    lines = ["error: could not compile `bank`", "Caused by: process didn't exit successfully"]
    found = diagnostics(tmp_path, monkeypatch, Language.RUST, lines)
    assert [(event["file"], event["message"]) for event in found] == [
        (None, line) for line in lines
    ]
