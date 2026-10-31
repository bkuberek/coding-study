"""`cstudy hint` on a project problem shows only the hints of its unlocked levels."""

from dataclasses import replace

import pytest

from coding_study.application.environment import Environment
from coding_study.application.reveal_hint import HintsLocked, RevealedHint, reveal_hint
from coding_study.application.start_attempt import StartRequest, start_attempt
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

HINTS = """
## Hints

### Hint 1

Keep balances in a dictionary.

### Hint 2

Check both accounts before moving money.
"""


@pytest.fixture
def environment(tmp_path) -> Environment:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    problem_md = tmp_path / "problems" / "0001-bank-project-python" / "problem.md"
    problem_md.write_text(problem_md.read_text(encoding="utf-8") + HINTS, encoding="utf-8")
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def hints_used(environment: Environment) -> int:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    return attempt.hints_used


def test_level_1s_hint_is_revealed(environment):
    assert reveal_hint(environment, None) == RevealedHint(
        PROJECT_SLUG, 1, 2, "Keep balances in a dictionary."
    )


def test_a_hint_of_a_locked_level_stays_hidden(environment):
    reveal_hint(environment, None)
    assert reveal_hint(environment, None) == HintsLocked(PROJECT_SLUG, 2)


def test_a_hidden_hint_is_not_counted(environment):
    reveal_hint(environment, None)
    reveal_hint(environment, None)
    assert hints_used(environment) == 1


def test_an_opened_level_reveals_its_hint(environment):
    reveal_hint(environment, None)
    attempt = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(attempt, level_unlocked=2))
    assert reveal_hint(environment, None) == RevealedHint(
        PROJECT_SLUG, 2, 2, "Check both accounts before moving money."
    )
