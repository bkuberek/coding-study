"""The cstudy actions IDEs offer (docs/specs/installation-and-workspaces.md#ide-files)."""

import pytest

from coding_study.domain.ide_actions import (
    DEBUG_ATTACH,
    DEBUG_CONNECT,
    DEBUG_LISTEN,
    PROBLEM_ACTIONS,
    WORKSPACE_ACTIONS,
    ProblemAction,
    Scope,
    WorkspaceAction,
    debug_name,
)
from coding_study.domain.layout import JVM_LANGUAGES
from coding_study.domain.problem import Language


def test_an_action_is_named_after_its_command_and_scope():
    action = ProblemAction(("test", "--perf"))
    assert action.name(Scope.CURRENT_FILE) == "cstudy test --perf (current file)"


def test_an_action_for_some_languages_names_them():
    action = ProblemAction(("test", "--typecheck"), languages=(Language.TYPESCRIPT,))
    expected = "cstudy test --typecheck (active attempt, TypeScript)"
    assert action.name(Scope.ACTIVE_ATTEMPT) == expected


def test_a_variant_is_part_of_the_name():
    done = next(action for action in PROBLEM_ACTIONS if action.command == "done")
    assert done.choice is not None
    gave_up = done.choice.variants[-1]
    assert done.name(Scope.CURRENT_FILE, gave_up) == "cstudy done --gave-up (current file)"


def test_a_workspace_action_is_named_after_its_command():
    assert WorkspaceAction(("stats",)).name == "cstudy stats"


def test_the_current_file_is_the_target():
    assert Scope.CURRENT_FILE.target("${file}") == ("${file}",)


def test_the_active_attempt_has_no_target():
    assert Scope.ACTIVE_ATTEMPT.target("${file}") == ()


def test_a_debug_configuration_names_its_languages():
    name = debug_name(Scope.CURRENT_FILE, (Language.JAVA, Language.KOTLIN))
    assert name == "Debug current file (Java, Kotlin)"


@pytest.mark.parametrize("command", ["test", "bench", "hint", "solution", "show", "done", "start"])
def test_every_command_taking_a_file_runs_on_the_current_file(command):
    commands = {action.command for action in PROBLEM_ACTIONS}
    assert command in commands


@pytest.mark.parametrize("command", ["solution", "show", "start"])
def test_a_command_requiring_a_target_has_no_active_attempt_variant(command):
    action = next(action for action in PROBLEM_ACTIONS if action.command == command)
    assert action.scopes == (Scope.CURRENT_FILE,)


def test_the_workspace_actions_are_next_stats_and_doctor():
    assert [action.name for action in WORKSPACE_ACTIONS] == [
        "cstudy next",
        "cstudy stats",
        "cstudy doctor",
    ]


def test_every_language_has_a_debug_port():
    assert {attach.language for attach in DEBUG_ATTACH} == set(Language)


def test_only_the_jvm_connects_to_a_listening_debugger():
    assert set(DEBUG_CONNECT.languages) == JVM_LANGUAGES


def test_debugging_runs_the_tests():
    assert DEBUG_LISTEN.arguments[:2] == ("test", "--debug")


def test_every_action_name_is_unique():
    names = [
        action.name(scope, variant)
        for action in (*PROBLEM_ACTIONS, DEBUG_LISTEN, DEBUG_CONNECT)
        for scope in action.scopes
        for variant in action.each_variant()
    ]
    assert len(names) == len(set(names))
