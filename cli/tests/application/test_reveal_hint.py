from pathlib import Path

import pytest

from coding_study.application.reveal_hint import RevealedHint, reveal_hint
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
FIRST_HINT = "For each value, which partner would complete the sum?"
SECOND_HINT = "Remember the values already seen, together with their positions."


@pytest.fixture
def environment(tmp_path: Path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(copy_repository(tmp_path, PRACTICE), toolchains=toolchains)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def hints_used(environment) -> int:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    return attempt.hints_used


def test_the_first_call_reveals_hint_1(environment):
    assert reveal_hint(environment, None) == RevealedHint("two-sum", 1, 2, FIRST_HINT)


def test_revealing_counts_the_hint_on_the_attempt(environment):
    reveal_hint(environment, None)
    assert hints_used(environment) == 1


def test_the_next_call_reveals_the_next_hint(environment):
    reveal_hint(environment, None)
    assert reveal_hint(environment, None) == RevealedHint("two-sum", 2, 2, SECOND_HINT)


def test_no_more_hints_after_the_last_one(environment):
    reveal_hint(environment, None)
    reveal_hint(environment, None)
    assert reveal_hint(environment, None) is None


def test_exhausted_hints_are_not_counted(environment):
    for _ in range(3):
        reveal_hint(environment, None)
    assert hints_used(environment) == 2


def test_an_explicit_slug_selects_its_attempt(environment):
    assert reveal_hint(environment, "two-sum") == RevealedHint("two-sum", 1, 2, FIRST_HINT)


def test_a_problem_without_an_attempt_is_a_usage_error(environment):
    with pytest.raises(UsageError):
        reveal_hint(environment, "lru-cache")


def test_no_attempt_in_progress_is_a_usage_error(tmp_path):
    environment = make_environment(copy_repository(tmp_path, PRACTICE))
    with pytest.raises(UsageError):
        reveal_hint(environment, None)
