"""The task table and the models a task uses (docs/specs/ai.md#routing)."""

import re

import pytest

from coding_study.domain.ai import AI_OFF, AiTask, ModelRef, Provider, Routing, Tier
from coding_study.domain.ai_routing import (
    CHECK_MESSAGE,
    CHECK_SCHEMA,
    TASKS,
    Target,
    TaskRefusedError,
    check_passed,
    ready_targets,
    sentence_start,
    targets_for,
    task_spec,
)
from coding_study.domain.config import AiSettings
from coding_study.domain.errors import UsageError

ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
OPENROUTER = ModelRef(Provider.OPENROUTER, "vendor/model:variant")
ALL_KEYS = frozenset(Provider)


def fixed(model: ModelRef | None = ANTHROPIC, enabled: bool = True) -> AiSettings:
    return AiSettings(enabled=enabled, routing=Routing.FIXED, model=model)


def auto(
    fast: ModelRef | None = OPENROUTER, strong: ModelRef | None = ANTHROPIC, enabled: bool = True
) -> AiSettings:
    return AiSettings(enabled=enabled, routing=Routing.AUTO, fast=fast, strong=strong)


def test_the_table_holds_the_limits_and_deadlines_of_each_task():
    review, check = task_spec(AiTask.REVIEW), task_spec(AiTask.CHECK)
    assert (review.max_output_tokens, review.deadline_s) == (16_000, 300)
    assert (check.max_output_tokens, check.deadline_s) == (1_000, 60)
    assert review.tiers == (Tier.STRONG,)
    assert check.tiers == (Tier.FAST, Tier.STRONG)
    assert set(TASKS) == set(AiTask)


@pytest.mark.parametrize("task", list(AiTask))
def test_fixed_routing_sends_every_task_to_the_model(task):
    assert targets_for(task, fixed()) == (Target(None, ANTHROPIC),)


def test_auto_routing_serves_review_from_the_strong_tier():
    assert targets_for(AiTask.REVIEW, auto()) == (Target(Tier.STRONG, ANTHROPIC),)


def test_auto_routing_checks_the_fast_tier_then_the_strong_one():
    assert targets_for(AiTask.CHECK, auto()) == (
        Target(Tier.FAST, OPENROUTER),
        Target(Tier.STRONG, ANTHROPIC),
    )


def test_a_check_of_two_tiers_with_the_same_model_goes_once_to_the_fast_tier():
    assert targets_for(AiTask.CHECK, auto(ANTHROPIC, ANTHROPIC)) == (Target(Tier.FAST, ANTHROPIC),)


def test_auto_review_does_not_need_the_fast_tier():
    assert targets_for(AiTask.REVIEW, auto(fast=None)) == (Target(Tier.STRONG, ANTHROPIC),)


def test_fixed_routing_without_a_model_is_refused():
    with pytest.raises(TaskRefusedError) as raised:
        targets_for(AiTask.REVIEW, fixed(None))
    assert str(raised.value) == (
        "ai.model is not set: choose the model of fixed routing in Settings or with "
        "cstudy config edit"
    )
    assert raised.value.brief == "ai.model is not set"


def test_auto_review_without_the_strong_tier_is_refused():
    with pytest.raises(TaskRefusedError) as raised:
        targets_for(AiTask.REVIEW, auto(strong=None))
    assert str(raised.value) == (
        "ai.strong is not set: auto routing serves AI review from the strong tier"
    )
    assert raised.value.brief == "ai.strong is not set"


def test_auto_check_names_the_first_unset_tier():
    with pytest.raises(
        TaskRefusedError, match=re.escape("ai.fast is not set: auto routing serves the check")
    ):
        targets_for(AiTask.CHECK, auto(fast=None, strong=None))
    with pytest.raises(TaskRefusedError, match=re.escape("ai.strong is not set")):
        targets_for(AiTask.CHECK, auto(strong=None))


def test_a_refusal_is_a_usage_error():
    with pytest.raises(UsageError):
        ready_targets(AiTask.REVIEW, fixed(enabled=False), ALL_KEYS)


@pytest.mark.parametrize("task", list(AiTask))
def test_ai_off_is_refused_before_a_model_or_a_key_is_looked_at(task):
    with pytest.raises(TaskRefusedError) as raised:
        ready_targets(task, fixed(None, enabled=False), frozenset())
    assert str(raised.value) == AI_OFF
    assert raised.value.brief == "AI is off"


def test_an_unset_model_is_refused_before_a_key_is_looked_at():
    with pytest.raises(TaskRefusedError, match=re.escape("ai.model is not set")):
        ready_targets(AiTask.REVIEW, fixed(None), frozenset())


def test_a_provider_without_a_key_is_refused_naming_the_tier_that_uses_it():
    with pytest.raises(TaskRefusedError) as raised:
        ready_targets(AiTask.REVIEW, auto(strong=OPENROUTER), frozenset({Provider.ANTHROPIC}))
    assert str(raised.value) == (
        "no key for openrouter, which the strong tier uses: cstudy ai key openrouter, or Settings"
    )
    assert raised.value.brief == "no key for openrouter"


def test_a_provider_without_a_key_under_fixed_routing_names_the_setting():
    with pytest.raises(
        TaskRefusedError, match=re.escape("no key for anthropic, which ai.model uses")
    ):
        ready_targets(AiTask.REVIEW, fixed(), frozenset())


def test_a_check_needs_a_key_for_each_model_and_names_the_first_without():
    keys = frozenset({Provider.ANTHROPIC})
    with pytest.raises(
        TaskRefusedError, match=re.escape("no key for openrouter, which the fast tier uses")
    ):
        ready_targets(AiTask.CHECK, auto(), keys)
    assert ready_targets(AiTask.CHECK, auto(), ALL_KEYS) == targets_for(AiTask.CHECK, auto())


def test_a_ready_task_returns_its_targets():
    assert ready_targets(AiTask.REVIEW, fixed(), ALL_KEYS) == (Target(None, ANTHROPIC),)


def test_the_check_asks_for_ok_true_in_a_portable_schema():
    assert CHECK_MESSAGE == 'Reply with {"ok": true}.'
    assert CHECK_SCHEMA["required"] == ["ok"]
    assert CHECK_SCHEMA["additionalProperties"] is False


@pytest.mark.parametrize(
    ("data", "passed"),
    [
        ({"ok": True}, True),
        ({"ok": False}, False),
        ({"ok": True, "extra": 1}, False),
        ({"ok": 1}, False),
        ({}, False),
        (None, False),
    ],
)
def test_a_check_passes_on_exactly_ok_true(data, passed):
    assert check_passed(data) is passed


def test_a_sentence_starts_with_a_capital():
    assert sentence_start("the check") == "The check"
    assert sentence_start("AI review") == "AI review"
    assert sentence_start("") == ""
