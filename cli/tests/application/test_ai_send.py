"""The send path's order and its usage rows (docs/specs/ai.md#routing, #consent and
#usage-and-the-daily-token-cap), over fakes of the three ports and a fake clock."""

import re
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from coding_study.application.ai_consent import RefusingAsker
from coding_study.application.ai_send import (
    AiPayload,
    ConsentQuestion,
    NotSent,
    Sent,
    SentItem,
    available_targets,
    consent_question,
    send,
)
from coding_study.application.environment import Environment
from coding_study.domain.ai import AI_OFF, AiTask, ApiKey, ModelRef, Provider, Routing, Tier
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from coding_study.domain.ai_records import CallOutcome, Consent, ModelCall
from coding_study.domain.ai_routing import Target, TaskRefusedError
from coding_study.domain.config import AiSettings, Config
from coding_study.domain.errors import UsageError
from tests.fakes import (
    NOW,
    FakeAiStore,
    FakeClock,
    FakeCredentials,
    ScriptedLanguageModels,
    make_environment,
)
from tests.fakes import (
    repository_root as copy_repository,
)

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
SECRET = "sk-sentinel-0123456789"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
OPENROUTER = ModelRef(Provider.OPENROUTER, "vendor/model:variant")
REVIEW_TARGET = Target(None, ANTHROPIC)
USAGE = Usage(900, 100, 0.00003)
COMPLETE = ModelReply(Ending.COMPLETE, '{"ok": true}', {"ok": True}, USAGE)
SCHEMA = {"type": "object"}


class Asker:
    def __init__(self, answer: bool = True) -> None:
        self.answer = answer
        self.questions: list[ConsentQuestion] = []

    def ask(self, question: ConsentQuestion) -> bool:
        self.questions.append(question)
        return self.answer


class InterruptedModels:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        self.requests.append(request)
        raise KeyboardInterrupt

    def list_models(self, provider: Provider, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        raise AssertionError("not asked")


def make(
    tmp_path: Path,
    *answers: ModelReply | ProviderError,
    ai: AiSettings | None = None,
    keys: dict[Provider, str] | None = None,
    **overrides: object,
) -> Environment:
    settings = ai or AiSettings(enabled=True, model=ANTHROPIC)
    parts: dict[str, object] = {
        "config": Config(ai=settings),
        "credentials": FakeCredentials({Provider.ANTHROPIC: SECRET} if keys is None else keys),
        "ai_store": FakeAiStore(),
        "models": ScriptedLanguageModels(*answers),
    }
    parts.update(overrides)
    return make_environment(copy_repository(tmp_path, PRACTICE), **parts)


def payload(**overrides: object) -> AiPayload:
    base = AiPayload(
        AiTask.REVIEW,
        "instructions",
        "message",
        (SentItem("instructions review-1", 2_100), SentItem("your notes", 4_200, "notes/a.md")),
        SCHEMA,
        "review",
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def stored_calls(environment: Environment) -> list[ModelCall]:
    store = environment.ai_store
    assert isinstance(store, FakeAiStore)
    return store.calls


def sent_requests(environment: Environment) -> list[ModelRequest]:
    models = environment.models
    assert isinstance(models, ScriptedLanguageModels)
    return models.requests


def test_a_consented_request_goes_to_the_model_and_writes_one_row(tmp_path):
    environment = make(tmp_path, COMPLETE)
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    asker = Asker()
    result = send(environment, REVIEW_TARGET, payload(), asker)
    assert isinstance(result, Sent)
    assert result.reply is COMPLETE
    assert asker.questions == []
    (request,) = sent_requests(environment)
    assert request == ModelRequest(
        ANTHROPIC, "instructions", "message", 16_000, 300, SCHEMA, "review"
    )
    assert environment.models.keys == [ApiKey(SECRET)]  # type: ignore[attr-defined]
    (call,) = stored_calls(environment)
    assert result.call == call
    assert call == ModelCall(
        purpose=AiTask.REVIEW,
        provider=Provider.ANTHROPIC,
        model="claude-x",
        tier=None,
        attempt_id=None,
        local_day=NOW.date(),
        started_at=NOW,
        ended_at=NOW,
        outcome=CallOutcome.OK,
        error=None,
        input_tokens=900,
        output_tokens=100,
        counted_tokens=1_000,
        cost_usd=0.00003,
    )


def test_the_row_holds_the_tier_and_the_attempt():
    pass


def test_the_row_holds_the_tier_the_attempt_and_the_local_day_of_the_start(tmp_path):
    ai = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER, strong=ANTHROPIC)
    environment = make(
        tmp_path, COMPLETE, ai=ai, keys={Provider.ANTHROPIC: SECRET, Provider.OPENROUTER: "k2"}
    )
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    send(environment, Target(Tier.STRONG, ANTHROPIC), payload(attempt_id=12), Asker())
    (call,) = stored_calls(environment)
    assert (call.tier, call.attempt_id, call.local_day) == (Tier.STRONG, 12, NOW.date())


def test_a_first_request_asks_and_a_yes_records_the_consent_and_sends(tmp_path):
    environment = make(tmp_path, COMPLETE)
    asker = Asker(True)
    result = send(environment, REVIEW_TARGET, payload(), asker)
    assert isinstance(result, Sent)
    consent = environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW)
    assert consent == Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW)
    assert environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.CHECK) is None
    assert len(sent_requests(environment)) == 1


def test_the_question_carries_what_is_sent_the_estimate_and_today_against_the_cap(tmp_path):
    environment = make(
        tmp_path, COMPLETE, ai=AiSettings(enabled=True, model=ANTHROPIC, daily_token_cap=50_000)
    )
    environment.ai_store.record_call(
        ModelCall(
            AiTask.CHECK, Provider.ANTHROPIC, "claude-x", None, None, NOW.date(), NOW, NOW,
            CallOutcome.OK, None, 40, 12, 52, None,
        )
    )  # fmt: skip
    asker = Asker()
    asked = payload(instructions="a" * 100, message="b" * 100)
    before = consent_question(environment, REVIEW_TARGET, asked)
    send(environment, REVIEW_TARGET, asked, asker)
    (question,) = asker.questions
    assert question == before
    assert question == ConsentQuestion(
        AiTask.REVIEW, REVIEW_TARGET, payload().items, 50, 16_000, 52, 50_000
    )


def test_a_no_sends_nothing_records_nothing_and_is_not_an_error(tmp_path):
    environment = make(tmp_path)
    result = send(environment, REVIEW_TARGET, payload(), Asker(False))
    assert result == NotSent(REVIEW_TARGET)
    assert sent_requests(environment) == []
    assert stored_calls(environment) == []
    assert environment.ai_store.consents() == ()


def test_consent_is_per_model_and_purpose(tmp_path):
    environment = make(tmp_path, COMPLETE)
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.CHECK, NOW))
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "other", AiTask.REVIEW, NOW))
    asker = Asker()
    send(environment, REVIEW_TARGET, payload(), asker)
    assert len(asker.questions) == 1


def test_a_refusing_asker_stops_the_request_with_the_command_to_record_consent(tmp_path):
    environment = make(tmp_path)
    with pytest.raises(UsageError) as raised:
        send(environment, REVIEW_TARGET, payload(), RefusingAsker())
    assert str(raised.value) == (
        "AI review needs your consent to send to anthropic:claude-x: run it once at a terminal, "
        "or cstudy ai consent anthropic:claude-x --purpose review"
    )
    assert sent_requests(environment) == []
    assert stored_calls(environment) == []
    assert environment.ai_store.consents() == ()


def test_ai_off_is_refused_first_even_with_a_key_and_a_consent(tmp_path):
    environment = make(tmp_path, ai=AiSettings(enabled=False, model=ANTHROPIC))
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    asker = Asker()
    with pytest.raises(TaskRefusedError) as raised:
        send(environment, REVIEW_TARGET, payload(), asker)
    assert str(raised.value) == AI_OFF
    assert (asker.questions, sent_requests(environment), stored_calls(environment)) == ([], [], [])


def test_an_unset_model_is_refused_before_the_keys_are_read(tmp_path):
    environment = make(tmp_path, ai=AiSettings(enabled=True), keys={})
    with pytest.raises(TaskRefusedError, match=re.escape("ai.model is not set")):
        available_targets(environment, AiTask.REVIEW)


def test_a_missing_key_is_refused_before_the_cap_and_the_consent(tmp_path):
    environment = make(tmp_path, keys={})
    asker = Asker()
    with pytest.raises(
        TaskRefusedError, match=re.escape("no key for anthropic, which ai.model uses")
    ):
        send(environment, REVIEW_TARGET, payload(), asker)
    assert (asker.questions, sent_requests(environment), stored_calls(environment)) == ([], [], [])


def test_the_cap_is_checked_before_the_consent_question(tmp_path):
    environment = make(
        tmp_path, ai=AiSettings(enabled=True, model=ANTHROPIC, daily_token_cap=16_009)
    )
    asker = Asker()
    with pytest.raises(UsageError) as raised:
        send(environment, REVIEW_TARGET, payload(instructions="x" * 40, message=""), asker)
    assert str(raised.value) == (
        "the daily token cap is reached: 0 of 16,009 tokens today, and this review needs up to "
        "16,010; raise ai.daily_token_cap or wait until tomorrow"
    )
    assert (asker.questions, sent_requests(environment), stored_calls(environment)) == ([], [], [])


def test_the_cap_counts_the_day_so_far_and_lets_a_request_that_fits_exactly_go(tmp_path):
    environment = make(
        tmp_path, COMPLETE, ai=AiSettings(enabled=True, model=ANTHROPIC, daily_token_cap=20_000)
    )
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    today = ModelCall(
        AiTask.REVIEW, Provider.ANTHROPIC, "claude-x", None, 1, NOW.date(), NOW, NOW,
        CallOutcome.OK, None, 3_000, 987, 3_990, None,
    )  # fmt: skip
    yesterday = replace(today, local_day=NOW.date() - timedelta(days=1), counted_tokens=9_999_999)
    environment.ai_store.record_call(today)
    environment.ai_store.record_call(yesterday)
    assert isinstance(
        send(environment, REVIEW_TARGET, payload(instructions="x", message=""), Asker()), Sent
    )
    with pytest.raises(
        UsageError, match=re.escape("the daily token cap is reached: 4,990 of 20,000 tokens today")
    ):
        send(environment, REVIEW_TARGET, payload(instructions="x" * 4_000, message=""), Asker())


def test_a_cap_refusal_leaves_the_request_unsent_and_the_store_as_it_was(tmp_path):
    environment = make(
        tmp_path, ai=AiSettings(enabled=True, model=ANTHROPIC, daily_token_cap=1_000)
    )
    with pytest.raises(UsageError, match=re.escape("the daily token cap is reached")):
        send(environment, REVIEW_TARGET, payload(), Asker())
    assert sent_requests(environment) == []
    assert stored_calls(environment) == []
    assert environment.ai_store.consents() == ()


def test_a_reply_without_a_usage_report_counts_its_estimate(tmp_path):
    environment = make(tmp_path, ModelReply(Ending.COMPLETE, "text"))
    result = send(
        environment, REVIEW_TARGET, payload(instructions="x" * 400, message="y" * 400), Asker()
    )
    assert isinstance(result, Sent)
    (call,) = stored_calls(environment)
    assert (call.input_tokens, call.output_tokens, call.cost_usd) == (None, None, None)
    assert call.counted_tokens == 200 + 16_000
    assert call.outcome is CallOutcome.OK


def test_a_reply_cut_by_the_output_limit_is_a_length_error_and_a_failed_row(tmp_path):
    environment = make(tmp_path, ModelReply(Ending.LENGTH, "cut", None, Usage(500, 16_000)))
    with pytest.raises(ProviderError) as raised:
        send(environment, REVIEW_TARGET, payload(), Asker())
    assert raised.value.kind is ProviderErrorKind.LENGTH
    assert str(raised.value) == (
        "the reply stopped at its 16,000-token limit before it was complete"
    )
    (call,) = stored_calls(environment)
    assert (call.outcome, call.error, call.counted_tokens) == (
        CallOutcome.FAILED,
        ProviderErrorKind.LENGTH,
        16_500,
    )


def test_a_declined_reply_is_a_refused_error_and_a_failed_row(tmp_path):
    environment = make(tmp_path, ModelReply(Ending.REFUSED, "", None, Usage(500, 3)))
    with pytest.raises(ProviderError) as raised:
        send(environment, REVIEW_TARGET, payload(), Asker())
    assert raised.value.kind is ProviderErrorKind.REFUSED
    assert str(raised.value) == "anthropic declined to answer this request"
    (call,) = stored_calls(environment)
    assert (call.outcome, call.error, call.counted_tokens) == (
        CallOutcome.FAILED,
        ProviderErrorKind.REFUSED,
        503,
    )


def test_a_provider_error_is_stored_with_the_tokens_it_reported_and_raised_again(tmp_path):
    failure = ProviderError(ProviderErrorKind.PROVIDER, "openrouter failed (502)", Usage(70, 0))
    environment = make(tmp_path, failure)
    with pytest.raises(ProviderError) as raised:
        send(environment, REVIEW_TARGET, payload(), Asker())
    assert raised.value is failure
    (call,) = stored_calls(environment)
    assert (call.outcome, call.error) == (CallOutcome.FAILED, ProviderErrorKind.PROVIDER)
    assert (call.input_tokens, call.output_tokens, call.counted_tokens) == (70, 0, 70)


def test_a_provider_error_without_usage_counts_the_estimate(tmp_path):
    environment = make(tmp_path, ProviderError(ProviderErrorKind.TIMEOUT, "no answer"))
    with pytest.raises(ProviderError):
        send(environment, REVIEW_TARGET, payload(instructions="x" * 40, message=""), Asker())
    (call,) = stored_calls(environment)
    assert (call.input_tokens, call.error, call.counted_tokens) == (
        None,
        ProviderErrorKind.TIMEOUT,
        16_010,
    )


def test_ctrl_c_stores_an_interrupted_row_with_the_estimate_and_goes_on(tmp_path):
    models = InterruptedModels()
    environment = make(tmp_path, models=models)
    with pytest.raises(KeyboardInterrupt):
        send(environment, REVIEW_TARGET, payload(instructions="x" * 40, message=""), Asker())
    (call,) = stored_calls(environment)
    assert (call.outcome, call.error, call.counted_tokens) == (
        CallOutcome.INTERRUPTED,
        None,
        16_010,
    )
    assert len(models.requests) == 1


def test_a_reply_the_task_rejects_is_a_failed_row_with_the_reported_tokens(tmp_path):
    def reject(reply: ModelReply) -> None:
        raise ProviderError(
            ProviderErrorKind.INVALID_REPLY,
            "the model's reply did not follow the review format: C4, C9 missing",
        )

    environment = make(tmp_path, COMPLETE)
    with pytest.raises(ProviderError) as raised:
        send(environment, REVIEW_TARGET, payload(accept=reject), Asker())
    assert raised.value.usage == USAGE
    (call,) = stored_calls(environment)
    assert (call.outcome, call.error, call.counted_tokens) == (
        CallOutcome.FAILED,
        ProviderErrorKind.INVALID_REPLY,
        1_000,
    )


def test_a_reply_the_task_accepts_is_an_ok_row(tmp_path):
    seen: list[ModelReply] = []
    environment = make(tmp_path, COMPLETE)
    result = send(environment, REVIEW_TARGET, payload(accept=seen.append), Asker())
    assert isinstance(result, Sent)
    assert seen == [COMPLETE]
    assert stored_calls(environment)[0].outcome is CallOutcome.OK


def test_a_target_the_task_does_not_name_is_a_programming_error(tmp_path):
    environment = make(tmp_path)
    with pytest.raises(ValueError, match=re.escape("is not a model of review")):
        send(environment, Target(None, OPENROUTER), payload(), Asker())


def test_a_check_goes_to_each_tier_and_needs_a_key_for_both(tmp_path):
    ai = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER, strong=ANTHROPIC)
    environment = make(tmp_path, ai=ai)
    with pytest.raises(
        TaskRefusedError, match=re.escape("no key for openrouter, which the fast tier uses")
    ):
        available_targets(environment, AiTask.CHECK)
    environment.credentials.save_key(Provider.OPENROUTER, ApiKey("k2"))
    assert available_targets(environment, AiTask.CHECK) == (
        Target(Tier.FAST, OPENROUTER),
        Target(Tier.STRONG, ANTHROPIC),
    )


def test_a_check_request_uses_the_checks_limit_and_deadline(tmp_path):
    environment = make(tmp_path, COMPLETE)
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.CHECK, NOW))
    send(environment, REVIEW_TARGET, payload(task=AiTask.CHECK), Asker())
    (request,) = sent_requests(environment)
    assert (request.max_output_tokens, request.deadline_s) == (1_000, 60)


def test_the_day_of_a_row_is_the_local_day_of_the_clock(tmp_path):
    late = datetime(2026, 11, 16, 23, 59, tzinfo=UTC)
    environment = make(tmp_path, COMPLETE, clock=FakeClock(late))
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, late))
    send(environment, REVIEW_TARGET, payload(), Asker())
    assert stored_calls(environment)[0].local_day == date(2026, 11, 16)
