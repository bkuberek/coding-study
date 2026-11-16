"""Consent to send (docs/specs/ai.md#consent), over a fake store and a fake clock."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from coding_study.application.ai_consent import (
    RefusingAsker,
    consent_needed,
    grant,
    parse_model,
    parse_purpose,
    revoke,
)
from coding_study.application.ai_send import ConsentQuestion
from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, ModelRef, Provider
from coding_study.domain.ai_records import Consent
from coding_study.domain.ai_routing import Target
from coding_study.domain.errors import UsageError
from tests.fakes import NOW, FakeAiStore, FakeClock, FakeCredentials, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
MODEL = ModelRef(Provider.ANTHROPIC, "claude-x")


def make(tmp_path: Path, clock: FakeClock | None = None) -> Environment:
    return make_environment(
        copy_repository(tmp_path, PRACTICE),
        ai_store=FakeAiStore(),
        credentials=FakeCredentials(),
        clock=clock or FakeClock(),
    )


def question(task: AiTask = AiTask.REVIEW) -> ConsentQuestion:
    return ConsentQuestion(task, Target(None, MODEL), (), 100, 16_000, 0, 500_000)


def test_a_model_is_a_provider_a_colon_and_an_id():
    assert parse_model("openrouter:vendor/model:variant") == ModelRef(
        Provider.OPENROUTER, "vendor/model:variant"
    )


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("claude", "expected provider:model, such as anthropic:<model id>"),
        ("gemini:x", 'unknown provider "gemini"; use one of anthropic, google, openai, openrouter'),
        ("openai:", 'no model id after "openai:"'),
        ("openai:a b", "a model id has no spaces"),
    ],
)
def test_text_that_is_no_model_is_a_usage_error(text, problem):
    with pytest.raises(UsageError) as raised:
        parse_model(text)
    assert str(raised.value) == f'"{text}" is not a model: {problem}'


@pytest.mark.parametrize("task", list(AiTask))
def test_each_purpose_is_known_by_its_name(task):
    assert parse_purpose(task.value) is task


@pytest.mark.parametrize("text", ["", "Review", "chat", "review,check"])
def test_another_purpose_is_a_usage_error(text):
    with pytest.raises(UsageError) as raised:
        parse_purpose(text)
    assert str(raised.value) == f'unknown purpose "{text}"; use one of review, check'


def test_granting_records_the_consent_now_for_that_model_and_purpose(tmp_path):
    environment = make(tmp_path)
    consent = grant(environment, MODEL, AiTask.REVIEW)
    assert consent == Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW)
    assert environment.ai_store.consents() == (consent,)


def test_granting_needs_no_key_and_works_with_ai_off(tmp_path):
    environment = make(tmp_path)
    assert environment.config.ai.enabled is False
    assert environment.credentials.keys_set() == frozenset()
    grant(environment, MODEL, AiTask.CHECK)
    assert environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.CHECK) is not None


def test_granting_again_keeps_the_first_time(tmp_path):
    environment = make(tmp_path)
    first = grant(environment, MODEL, AiTask.REVIEW)
    environment.clock.current = datetime(2026, 11, 1, tzinfo=UTC)  # type: ignore[attr-defined]
    assert grant(environment, MODEL, AiTask.REVIEW) == first
    assert environment.ai_store.consents() == (first,)


def test_a_consent_covers_one_model_and_one_purpose(tmp_path):
    environment = make(tmp_path)
    grant(environment, MODEL, AiTask.REVIEW)
    store = environment.ai_store
    assert store.consent(Provider.ANTHROPIC, "claude-x", AiTask.CHECK) is None
    assert store.consent(Provider.ANTHROPIC, "claude-y", AiTask.REVIEW) is None
    assert store.consent(Provider.OPENAI, "claude-x", AiTask.REVIEW) is None


def test_revoking_removes_only_that_consent(tmp_path):
    environment = make(tmp_path)
    grant(environment, MODEL, AiTask.REVIEW)
    kept = grant(environment, MODEL, AiTask.CHECK)
    assert revoke(environment, MODEL, AiTask.REVIEW) is True
    assert environment.ai_store.consents() == (kept,)


def test_revoking_what_was_never_granted_says_so(tmp_path):
    environment = make(tmp_path)
    assert revoke(environment, MODEL, AiTask.REVIEW) is False


def test_a_revoked_consent_is_asked_for_again(tmp_path):
    environment = make(tmp_path)
    grant(environment, MODEL, AiTask.REVIEW)
    revoke(environment, MODEL, AiTask.REVIEW)
    assert environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW) is None
    assert grant(environment, MODEL, AiTask.REVIEW).granted_at == NOW


def test_without_a_terminal_the_review_message_names_the_command_to_run():
    assert consent_needed(question(AiTask.REVIEW)) == (
        "AI review needs your consent to send to anthropic:claude-x: run it once at a terminal, "
        "or cstudy ai consent anthropic:claude-x --purpose review"
    )


def test_without_a_terminal_the_check_message_starts_a_sentence():
    assert consent_needed(question(AiTask.CHECK)) == (
        "The check needs your consent to send to anthropic:claude-x: run it once at a terminal, "
        "or cstudy ai consent anthropic:claude-x --purpose check"
    )


def test_the_refusing_asker_never_says_yes():
    with pytest.raises(UsageError) as raised:
        RefusingAsker().ask(question())
    assert str(raised.value) == consent_needed(question())
