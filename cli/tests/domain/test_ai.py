"""The AI preview's vocabulary and records (docs/specs/ai.md#settings, #keys and #errors)."""

import logging
import re
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from coding_study.domain.ai import (
    KEY_SHAPE,
    AiTask,
    ApiKey,
    ModelRef,
    Provider,
    Routing,
    Tier,
)
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from coding_study.domain.ai_records import (
    REVIEW_FORMAT,
    CallOutcome,
    Consent,
    ModelCall,
    ReviewItem,
    ReviewRecord,
    Verdict,
)
from coding_study.domain.config import DEFAULT_DAILY_TOKEN_CAP, AiSettings, Config
from coding_study.domain.errors import UsageError

SENTINEL = "sk-sentinel-0123456789abcdef"
NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)


def test_the_providers_are_the_four_of_the_owner_s_list_in_the_order_of_credentials_toml():
    assert [provider.value for provider in Provider] == [
        "anthropic",
        "google",
        "openai",
        "openrouter",
    ]


def test_the_routings_tiers_and_tasks_have_the_words_the_spec_uses():
    assert [routing.value for routing in Routing] == ["fixed", "auto"]
    assert [tier.value for tier in Tier] == ["fast", "strong"]
    assert [task.value for task in AiTask] == ["review", "check"]


@pytest.mark.parametrize(
    ("text", "provider", "model_id"),
    [
        ("anthropic:claude-x", Provider.ANTHROPIC, "claude-x"),
        ("google:gemini-x", Provider.GOOGLE, "gemini-x"),
        ("openai:gpt-x", Provider.OPENAI, "gpt-x"),
        ("openrouter:vendor/model:variant", Provider.OPENROUTER, "vendor/model:variant"),
        ("openai:a:b:c", Provider.OPENAI, "a:b:c"),
    ],
)
def test_a_model_splits_at_the_first_colon(text, provider, model_id):
    model = ModelRef.parse(text)
    assert (model.provider, model.model_id) == (provider, model_id)


@pytest.mark.parametrize("text", ["anthropic:claude-x", "openrouter:vendor/model:variant"])
def test_a_model_prints_as_it_was_written(text):
    assert str(ModelRef.parse(text)) == text


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("claude-x", "expected provider:model, such as anthropic:<model id>"),
        ("", "expected provider:model, such as anthropic:<model id>"),
        (
            "gemini:x",
            'unknown provider "gemini"; use one of anthropic, google, openai, openrouter',
        ),
        (":x", 'unknown provider ""; use one of anthropic, google, openai, openrouter'),
        ("OpenAI:x", 'unknown provider "OpenAI"; use one of anthropic, google, openai, openrouter'),
        ("openai:", 'no model id after "openai:"'),
        ("openai:two words", "a model id has no spaces"),
        ("openai:tab\there", "a model id has no spaces"),
        ("openai:new\nline", "a model id has no spaces"),
        ("openai: leading", "a model id has no spaces"),
    ],
)
def test_a_model_the_shape_refuses_says_why(text, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        ModelRef.parse(text)


@given(
    provider=st.sampled_from(list(Provider)),
    model_id=st.text(
        alphabet=st.characters(blacklist_categories=["Z", "C"]), min_size=1, max_size=40
    ),
)
def test_any_model_id_without_spaces_round_trips(provider, model_id):
    model = ModelRef.parse(f"{provider}:{model_id}")
    assert (model.provider, model.model_id) == (provider, model_id)
    assert ModelRef.parse(str(model)) == model


def test_a_key_prints_as_key_everywhere():
    key = ApiKey(SENTINEL)
    percent = ["%s" % key, "%r" % key]  # noqa: UP031
    shown = [repr(key), str(key), f"{key}", f"{key!r}", f"{key:>20}", *percent]
    assert shown == ["<key>"] * len(shown)


def test_a_key_stays_hidden_inside_containers_and_dataclasses():
    key = ApiKey(SENTINEL)
    holders = [
        [key],
        (key,),
        {Provider.OPENAI: key},
        {"k": [key]},
        replace(AiSettings(), model=None),
        ValueError(key),
    ]
    assert SENTINEL not in " ".join(f"{holder!r} {holder}" for holder in holders)


def test_a_key_does_not_reach_a_log_record(caplog):
    key = ApiKey(SENTINEL)
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("coding_study.test").warning("sending with %s and %r", key, key)
        logging.getLogger("coding_study.test").warning("sending with %(key)s", {"key": key})
    assert SENTINEL not in caplog.text
    assert "<key>" in caplog.text


def test_only_reveal_gives_the_key_back():
    assert ApiKey(SENTINEL).reveal() == SENTINEL


def test_a_key_equals_a_key_with_the_same_text():
    assert ApiKey(SENTINEL) == ApiKey(SENTINEL)
    assert ApiKey(SENTINEL) != ApiKey("another")
    assert ApiKey(SENTINEL) != SENTINEL
    assert len({ApiKey(SENTINEL), ApiKey(SENTINEL)}) == 1


@pytest.mark.parametrize("text", ["", " ", "two words", "tab\tkey", "line\nbreak", "bell\x07"])
def test_a_key_is_one_line_of_text_with_no_spaces(text):
    with pytest.raises(UsageError, match=KEY_SHAPE):
        ApiKey(text)


def test_the_message_for_a_bad_key_does_not_hold_it():
    with pytest.raises(UsageError) as raised:
        ApiKey("two words")
    assert str(raised.value) == "a key is one line of text with no spaces"


def test_scrub_replaces_the_key_in_text_a_provider_sent_back():
    key = ApiKey(SENTINEL)
    text = f'invalid key {SENTINEL}; got "{SENTINEL}"'
    assert key.scrub(text) == 'invalid key <key>; got "<key>"'
    assert key.scrub("no key here") == "no key here"


def test_the_ai_settings_default_to_off_fixed_routing_and_a_500000_token_cap():
    settings = Config().ai
    assert settings == AiSettings(
        enabled=False,
        routing=Routing.FIXED,
        model=None,
        fast=None,
        strong=None,
        daily_token_cap=500_000,
    )
    assert DEFAULT_DAILY_TOKEN_CAP == 500_000


def test_a_request_needs_an_output_limit_and_a_deadline():
    model = ModelRef(Provider.OPENAI, "gpt-x")
    request = ModelRequest(model, "instructions", "message", 1_000, 60.0)
    assert (request.schema, request.schema_name) == (None, "reply")
    with pytest.raises(ValueError, match="output limit"):
        ModelRequest(model, "i", "m", 0, 60.0)
    with pytest.raises(ValueError, match="deadline"):
        ModelRequest(model, "i", "m", 1_000, 0)


def test_usage_adds_input_and_output_and_knows_a_cost_only_when_reported():
    assert Usage(1_200, 300).total_tokens == 1_500
    assert Usage(1_200, 300).cost_usd is None
    assert Usage(1_200, 300, 0.00003).cost_usd == 0.00003


def test_a_reply_may_end_cut_or_refused_without_an_error():
    assert [ending.value for ending in Ending] == ["complete", "length", "refused"]
    reply = ModelReply(Ending.LENGTH, usage=Usage(10, 16_000))
    assert (reply.text, reply.data) == ("", None)


def test_the_error_kinds_are_the_ones_the_spec_stores():
    assert [kind.value for kind in ProviderErrorKind] == [
        "auth",
        "rate_limit",
        "model",
        "refused",
        "length",
        "network",
        "timeout",
        "provider",
        "invalid_reply",
    ]


def test_a_provider_error_carries_its_kind_and_the_tokens_it_reported():
    error = ProviderError(
        ProviderErrorKind.AUTH,
        "anthropic refused the key (401): set it again with cstudy ai key anthropic",
        Usage(5, 0),
    )
    assert (
        str(error) == "anthropic refused the key (401): set it again with cstudy ai key anthropic"
    )
    assert (error.kind, error.usage) == (ProviderErrorKind.AUTH, Usage(5, 0))
    assert ProviderError(ProviderErrorKind.TIMEOUT, "late").usage is None


def test_a_call_names_what_the_cap_counts():
    call = ModelCall(
        purpose=AiTask.CHECK,
        provider=Provider.OPENROUTER,
        model="vendor/model",
        tier=Tier.FAST,
        attempt_id=None,
        local_day=date(2026, 11, 16),
        started_at=NOW,
        ended_at=NOW,
        outcome=CallOutcome.FAILED,
        error=ProviderErrorKind.TIMEOUT,
        input_tokens=None,
        output_tokens=None,
        counted_tokens=1_250,
        cost_usd=None,
    )
    assert (call.counted_tokens, call.input_tokens) == (1_250, None)
    assert [outcome.value for outcome in CallOutcome] == ["ok", "failed", "interrupted"]


def test_a_consent_is_per_provider_model_and_purpose():
    consent = Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW)
    assert consent != replace(consent, purpose=AiTask.CHECK)
    assert consent != replace(consent, model="claude-y")
    assert consent != replace(consent, provider=Provider.OPENAI)


def test_a_review_is_format_1_until_the_store_numbers_it_and_unless_dismissed():
    item = ReviewItem(1, "Requirements", "States the scope", Verdict.PARTIAL, ("a quote",), "gap")
    record = ReviewRecord(
        attempt_id=12,
        created_at=NOW,
        provider=Provider.ANTHROPIC,
        model="claude-x",
        prompt_version="review-1",
        rubric_sha256="0" * 64,
        notes_sha256="1" * 64,
        items=(item,),
        summary="Strong on the API.",
        quotes_dropped=0,
        input_tokens=9_812,
        output_tokens=2_410,
        cost_usd=None,
    )
    assert (record.id, record.format, record.dismissed_at) == (None, REVIEW_FORMAT, None)
    assert REVIEW_FORMAT == 1
    assert [verdict.value for verdict in Verdict] == ["met", "partial", "missing"]
