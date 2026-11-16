"""The check and the model listing (docs/specs/ai.md#the-check and #routing), over fakes of the
ports and a clock that moves."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from coding_study.application.ai_check import (
    CheckOutcome,
    CheckResult,
    check_payload,
    run_check,
)
from coding_study.application.ai_consent import RefusingAsker
from coding_study.application.ai_models import LIST_DEADLINE_S, list_provider_models
from coding_study.application.ai_send import ConsentQuestion, available_targets
from coding_study.application.environment import Environment
from coding_study.domain.ai import AI_OFF, AiTask, ApiKey, ModelRef, Provider, Routing, Tier
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from coding_study.domain.ai_records import CallOutcome, Consent
from coding_study.domain.ai_routing import (
    CHECK_INSTRUCTIONS,
    CHECK_MESSAGE,
    CHECK_SCHEMA,
    Target,
    TaskRefusedError,
)
from coding_study.domain.config import AiSettings, Config
from coding_study.domain.errors import UsageError
from tests.fakes import (
    NOW,
    FakeAiStore,
    FakeClock,
    FakeCredentials,
    ScriptedLanguageModels,
    make_environment,
    repository_root,
)

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
SECRET = "sk-sentinel-0123456789"
FAST = ModelRef(Provider.OPENROUTER, "vendor/model")
STRONG = ModelRef(Provider.ANTHROPIC, "claude-x")
AUTO = AiSettings(enabled=True, routing=Routing.AUTO, fast=FAST, strong=STRONG)
FIXED = AiSettings(enabled=True, model=STRONG)
KEYS = {Provider.ANTHROPIC: SECRET, Provider.OPENROUTER: SECRET + "2"}
PASSED = ModelReply(Ending.COMPLETE, '{"ok": true}', {"ok": True}, Usage(40, 12, 0.00003))


class SlowClock(FakeClock):
    """Every reading is 1.4 s after the one before."""

    def now(self) -> datetime:
        self.current += timedelta(seconds=1.4)
        return self.current


class Asker:
    def __init__(self, *answers: bool) -> None:
        self.answers = list(answers)
        self.questions: list[ConsentQuestion] = []

    def ask(self, question: ConsentQuestion) -> bool:
        self.questions.append(question)
        return self.answers.pop(0)


def make(
    tmp_path: Path,
    *answers: ModelReply | ProviderError,
    ai: AiSettings = AUTO,
    keys: dict[Provider, str] | None = None,
    **overrides: object,
) -> Environment:
    parts: dict[str, object] = {
        "config": Config(ai=ai),
        "credentials": FakeCredentials(KEYS if keys is None else keys),
        "ai_store": FakeAiStore(),
        "models": ScriptedLanguageModels(*answers),
        "clock": SlowClock(NOW),
    }
    parts.update(overrides)
    return make_environment(repository_root(tmp_path, PRACTICE), **parts)


def consent_to(environment: Environment, *models: ModelRef) -> None:
    for model in models:
        environment.ai_store.grant_consent(
            Consent(model.provider, model.model_id, AiTask.CHECK, NOW)
        )


def run(environment: Environment, asker=None) -> list[CheckResult]:
    targets = available_targets(environment, AiTask.CHECK)
    return list(run_check(environment, targets, asker or RefusingAsker()))


def scripted(environment: Environment) -> ScriptedLanguageModels:
    assert isinstance(environment.models, ScriptedLanguageModels)
    return environment.models


def stored(environment: Environment) -> FakeAiStore:
    assert isinstance(environment.ai_store, FakeAiStore)
    return environment.ai_store


# the check


def test_each_model_the_routing_names_is_asked_for_ok_in_the_schema(tmp_path):
    environment = make(tmp_path, PASSED, PASSED)
    consent_to(environment, FAST, STRONG)
    run(environment)
    fast, strong = scripted(environment).requests
    assert [request.model for request in scripted(environment).requests] == [FAST, STRONG]
    assert (fast.instructions, fast.message, fast.schema) == (
        CHECK_INSTRUCTIONS,
        CHECK_MESSAGE,
        CHECK_SCHEMA,
    )
    assert (fast.max_output_tokens, fast.deadline_s) == (1_000, 60)
    assert strong == fast.__class__(
        STRONG, fast.instructions, fast.message, 1_000, 60, CHECK_SCHEMA, fast.schema_name
    )
    assert scripted(environment).keys == [ApiKey(SECRET + "2"), ApiKey(SECRET)]


def test_a_passing_check_reports_the_time_and_the_tokens_the_provider_reported(tmp_path):
    environment = make(tmp_path, PASSED, PASSED)
    consent_to(environment, FAST, STRONG)
    fast, strong = run(environment)
    assert (fast.target, fast.outcome) == (Target(Tier.FAST, FAST), CheckOutcome.PASSED)
    assert (fast.seconds, fast.usage, fast.error) == (pytest.approx(1.4), PASSED.usage, None)
    assert strong.target == Target(Tier.STRONG, STRONG)


def test_each_request_is_a_check_row_with_its_tier(tmp_path):
    environment = make(tmp_path, PASSED, PASSED)
    consent_to(environment, FAST, STRONG)
    run(environment)
    rows = stored(environment).calls
    assert [(row.purpose, row.model, row.tier, row.outcome) for row in rows] == [
        (AiTask.CHECK, "vendor/model", Tier.FAST, CallOutcome.OK),
        (AiTask.CHECK, "claude-x", Tier.STRONG, CallOutcome.OK),
    ]


def test_fixed_routing_checks_the_one_model_without_a_tier(tmp_path):
    environment = make(tmp_path, PASSED, ai=FIXED)
    consent_to(environment, STRONG)
    (result,) = run(environment)
    assert result.target == Target(None, STRONG)
    assert len(scripted(environment).requests) == 1


def test_auto_routing_with_one_model_for_both_tiers_checks_it_once(tmp_path):
    same = AiSettings(enabled=True, routing=Routing.AUTO, fast=STRONG, strong=STRONG)
    environment = make(tmp_path, PASSED, ai=same)
    consent_to(environment, STRONG)
    (result,) = run(environment)
    assert result.target == Target(Tier.FAST, STRONG)


def test_a_failing_tier_is_reported_and_the_next_model_is_still_checked(tmp_path):
    refused = ProviderError(
        ProviderErrorKind.AUTH,
        "openrouter refused the key (401): set it again with cstudy ai key openrouter",
    )
    environment = make(tmp_path, refused, PASSED)
    consent_to(environment, FAST, STRONG)
    fast, strong = run(environment)
    assert (fast.outcome, fast.error, fast.seconds) == (CheckOutcome.FAILED, str(refused), None)
    assert strong.outcome is CheckOutcome.PASSED
    rows = stored(environment).calls
    assert [(row.outcome, row.error) for row in rows] == [
        (CallOutcome.FAILED, ProviderErrorKind.AUTH),
        (CallOutcome.OK, None),
    ]


@pytest.mark.parametrize(
    "reply",
    [
        ModelReply(Ending.COMPLETE, '{"ok": false}', {"ok": False}, Usage(40, 12)),
        ModelReply(Ending.COMPLETE, '{"ok": true, "x": 1}', {"ok": True, "x": 1}, Usage(40, 12)),
        ModelReply(Ending.COMPLETE, "ok", None, Usage(40, 12)),
    ],
)
def test_a_reply_that_is_not_ok_true_fails_as_an_invalid_reply_with_its_tokens(tmp_path, reply):
    environment = make(tmp_path, reply, ai=FIXED)
    consent_to(environment, STRONG)
    (result,) = run(environment)
    assert result.outcome is CheckOutcome.FAILED
    assert result.error == (
        'the model\'s reply did not follow the check format: it is not {"ok": true}'
    )
    (row,) = stored(environment).calls
    assert (row.outcome, row.error, row.input_tokens) == (
        CallOutcome.FAILED,
        ProviderErrorKind.INVALID_REPLY,
        40,
    )


def test_a_cut_reply_and_a_refusal_fail_the_check(tmp_path):
    cut = ModelReply(Ending.LENGTH, "{", None, Usage(40, 1_000))
    refused = ModelReply(Ending.REFUSED)
    environment = make(tmp_path, cut, refused)
    consent_to(environment, FAST, STRONG)
    fast, strong = run(environment)
    assert (fast.outcome, fast.error) == (
        CheckOutcome.FAILED,
        "the reply stopped at its 1,000-token limit before it was complete",
    )
    assert (strong.outcome, strong.error) == (
        CheckOutcome.FAILED,
        "anthropic declined to answer this request",
    )


def test_consent_is_asked_for_each_model_without_one_and_recorded_on_yes(tmp_path):
    environment = make(tmp_path, PASSED, PASSED)
    consent_to(environment, STRONG)
    asker = Asker(True)
    run(environment, asker)
    (question,) = asker.questions
    assert (question.task, question.target) == (AiTask.CHECK, Target(Tier.FAST, FAST))
    assert [(item.name, item.size_bytes) for item in question.items] == [
        ("instructions check-1", len(CHECK_INSTRUCTIONS)),
        ("a fixed test message", len(CHECK_MESSAGE)),
        ("nothing of yours", None),
    ]
    assert stored(environment).consent(Provider.OPENROUTER, "vendor/model", AiTask.CHECK)


def test_a_no_sends_nothing_to_that_model_and_goes_on_to_the_next(tmp_path):
    environment = make(tmp_path, PASSED)
    consent_to(environment, STRONG)
    fast, strong = run(environment, Asker(False))
    assert (fast.outcome, strong.outcome) == (CheckOutcome.NOT_SENT, CheckOutcome.PASSED)
    assert [request.model for request in scripted(environment).requests] == [STRONG]
    assert stored(environment).consent(Provider.OPENROUTER, "vendor/model", AiTask.CHECK) is None


def test_a_missing_consent_without_a_terminal_refuses_before_sending(tmp_path):
    environment = make(tmp_path, PASSED, PASSED)
    with pytest.raises(
        UsageError, match="cstudy ai consent openrouter:vendor/model --purpose check"
    ):
        run(environment)
    assert scripted(environment).requests == []
    assert stored(environment).calls == []


def test_the_daily_cap_refuses_before_sending(tmp_path):
    capped = AiSettings(
        enabled=True, routing=Routing.AUTO, fast=FAST, strong=STRONG, daily_token_cap=100
    )
    environment = make(tmp_path, PASSED, PASSED, ai=capped)
    consent_to(environment, FAST, STRONG)
    with pytest.raises(UsageError, match="the daily token cap is reached"):
        run(environment)
    assert scripted(environment).requests == []


def test_ctrl_c_stores_an_interrupted_row_and_stops_the_check(tmp_path):
    class Interrupted(ScriptedLanguageModels):
        def complete(self, request, key):
            raise KeyboardInterrupt

    environment = make(tmp_path, models=Interrupted(), ai=FIXED)
    consent_to(environment, STRONG)
    with pytest.raises(KeyboardInterrupt):
        run(environment)
    (row,) = stored(environment).calls
    assert (row.purpose, row.outcome) == (AiTask.CHECK, CallOutcome.INTERRUPTED)


def test_the_payload_names_the_check_and_sends_nothing_of_the_learner(tmp_path):
    payload = check_payload()
    assert (payload.task, payload.instructions, payload.message) == (
        AiTask.CHECK,
        CHECK_INSTRUCTIONS,
        CHECK_MESSAGE,
    )
    assert payload.attempt_id is None


@pytest.mark.parametrize(
    ("settings", "keys", "message"),
    [
        (AiSettings(), KEYS, AI_OFF),
        (AiSettings(enabled=True), KEYS, "ai.model is not set"),
        (FIXED, {}, "no key for anthropic, which ai.model uses"),
    ],
)
def test_a_check_that_cannot_run_is_refused_before_anything_is_sent(
    tmp_path, settings, keys, message
):
    environment = make(tmp_path, ai=settings, keys=keys, models=ScriptedLanguageModels())
    with pytest.raises(TaskRefusedError, match=re.escape(message)):
        run(environment)
    assert scripted(environment).requests == []


# listing a provider's models


def list_models(environment: Environment, provider: Provider) -> tuple[str, ...]:
    return list_provider_models(
        environment.config.ai, environment.credentials, environment.models, provider
    )


def test_a_listing_is_sorted_and_asked_with_the_providers_key_and_its_deadline(tmp_path):
    environment = make(tmp_path)
    scripted(environment).listings[Provider.ANTHROPIC] = ("claude-b", "claude-a")
    requested: list[tuple[Provider, ApiKey, float]] = []
    listed = scripted(environment).list_models

    def spy(provider, key, deadline_s):
        requested.append((provider, key, deadline_s))
        return listed(provider, key, deadline_s)

    scripted(environment).list_models = spy  # type: ignore[method-assign]
    assert list_models(environment, Provider.ANTHROPIC) == ("claude-a", "claude-b")
    assert requested == [(Provider.ANTHROPIC, ApiKey(SECRET), LIST_DEADLINE_S)]
    assert LIST_DEADLINE_S == 30


def test_a_listing_sends_no_model_request_and_writes_no_row_or_consent(tmp_path):
    environment = make(tmp_path)
    list_models(environment, Provider.OPENROUTER)
    assert scripted(environment).requests == []
    assert (stored(environment).calls, stored(environment).consents()) == ([], ())


def test_a_listing_needs_no_model_settings(tmp_path):
    environment = make(tmp_path, ai=AiSettings(enabled=True))
    assert list_models(environment, Provider.ANTHROPIC) == ()


def test_a_listing_with_ai_off_is_refused(tmp_path):
    environment = make(tmp_path, ai=AiSettings())
    with pytest.raises(UsageError, match="AI is off"):
        list_models(environment, Provider.ANTHROPIC)
    assert scripted(environment).listed == []


def test_a_listing_without_the_providers_key_is_refused_before_a_request(tmp_path):
    environment = make(tmp_path)
    with pytest.raises(UsageError, match="no key for google: cstudy ai key google, or Settings"):
        list_models(environment, Provider.GOOGLE)
    assert scripted(environment).listed == []


def test_a_provider_failure_is_raised_without_the_key(tmp_path):
    failure = ProviderError(ProviderErrorKind.PROVIDER, "openai failed (502): bad gateway")
    environment = make(tmp_path, keys={Provider.OPENAI: SECRET})
    scripted(environment).listings[Provider.OPENAI] = failure
    with pytest.raises(ProviderError) as raised:
        list_models(environment, Provider.OPENAI)
    assert SECRET not in str(raised.value)
