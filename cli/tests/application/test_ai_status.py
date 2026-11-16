"""`cstudy ai status` and `cstudy ai usage` (docs/specs/cli.md#cstudy-ai-status and
#cstudy-ai-usage), over fakes and a fake clock."""

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.ai_status import ai_status
from coding_study.application.ai_usage import usage_report
from coding_study.application.environment import Environment
from coding_study.domain.ai import AI_OFF, AiTask, ModelRef, Provider, Routing, Tier
from coding_study.domain.ai_records import CallOutcome, Consent, ModelCall
from coding_study.domain.ai_routing import Target
from coding_study.domain.config import AiSettings, Config
from coding_study.domain.errors import UsageError
from tests.fakes import NOW, FakeAiStore, FakeCredentials, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
OPENROUTER = ModelRef(Provider.OPENROUTER, "vendor/model")
TODAY = NOW.date()
AUTO = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER, strong=ANTHROPIC)


def make(
    tmp_path: Path,
    ai: AiSettings,
    keys: dict[Provider, str] | None = None,
    issue: str | None = None,
) -> Environment:
    return make_environment(
        copy_repository(tmp_path, PRACTICE),
        config=Config(ai=ai),
        ai_store=FakeAiStore(),
        credentials=FakeCredentials(keys or {}, issue),
    )


def call(
    day: date = TODAY,
    provider: Provider = Provider.ANTHROPIC,
    model: str = "claude-x",
    purpose: AiTask = AiTask.REVIEW,
    outcome: CallOutcome = CallOutcome.OK,
    counted: int = 1_000,
    cost: float | None = None,
) -> ModelCall:
    return ModelCall(
        purpose,
        provider,
        model,
        None,
        None,
        day,
        NOW,
        NOW,
        outcome,
        None,
        None,
        None,
        counted,
        cost,
    )


def record(environment: Environment, *calls: ModelCall) -> None:
    for each in calls:
        environment.ai_store.record_call(each)


def test_the_defaults_say_off_with_nothing_set_and_nothing_stored(tmp_path):
    status = ai_status(make(tmp_path, AiSettings()))
    assert (status.enabled, status.routing) == (False, Routing.FIXED)
    assert (status.model, status.fast, status.strong) == (None, None, None)
    assert status.credentials.keys == frozenset()
    assert status.credentials.issue is None
    assert status.consents == ()
    assert status.today.day == TODAY
    assert status.today.cap == 500_000
    assert status.today.counters.requests == 0
    assert status.today.counters.cost_usd is None


def test_every_task_is_listed_with_why_it_cannot_run_while_ai_is_off(tmp_path):
    status = ai_status(make(tmp_path, AiSettings(model=ANTHROPIC), {Provider.ANTHROPIC: "k"}))
    assert [task.task for task in status.tasks] == [AiTask.REVIEW, AiTask.CHECK]
    for task in status.tasks:
        assert task.ready is False
        assert task.reason == AI_OFF
        assert task.brief == "AI is off"
        assert task.targets == (Target(None, ANTHROPIC),)


def test_fixed_routing_with_a_key_is_ready_for_each_task(tmp_path):
    status = ai_status(
        make(tmp_path, AiSettings(enabled=True, model=ANTHROPIC), {Provider.ANTHROPIC: "k"})
    )
    for task in status.tasks:
        assert (task.ready, task.reason, task.brief) == (True, None, None)
        assert task.targets == (Target(None, ANTHROPIC),)
    assert status.credentials.keys == frozenset({Provider.ANTHROPIC})


def test_auto_routing_reviews_with_the_strong_tier_and_checks_both(tmp_path):
    keys = {Provider.ANTHROPIC: "k", Provider.OPENROUTER: "k2"}
    review, check = ai_status(make(tmp_path, AUTO, keys)).tasks
    assert review.targets == (Target(Tier.STRONG, ANTHROPIC),)
    assert check.targets == (Target(Tier.FAST, OPENROUTER), Target(Tier.STRONG, ANTHROPIC))
    assert review.ready
    assert check.ready


def test_a_task_whose_model_is_unset_has_no_models_and_says_which_key(tmp_path):
    status = ai_status(make(tmp_path, replace(AUTO, strong=None), {Provider.OPENROUTER: "k"}))
    review, check = status.tasks
    assert (review.targets, review.ready, review.brief) == ((), False, "ai.strong is not set")
    assert (
        review.reason == "ai.strong is not set: auto routing serves AI review from the strong tier"
    )
    assert check.targets == ()
    assert check.brief == "ai.strong is not set"
    assert status.strong is None
    assert status.fast == OPENROUTER


def test_a_task_whose_provider_has_no_key_lists_its_models_and_names_the_provider(tmp_path):
    review, check = ai_status(make(tmp_path, AUTO, {Provider.ANTHROPIC: "k"})).tasks
    assert review.ready is True
    assert check.ready is False
    assert check.brief == "no key for openrouter"
    assert check.reason == (
        "no key for openrouter, which the fast tier uses: cstudy ai key openrouter, or Settings"
    )
    assert check.targets == (Target(Tier.FAST, OPENROUTER), Target(Tier.STRONG, ANTHROPIC))


def test_a_credentials_file_that_does_not_load_is_reported_and_blocks_the_tasks(tmp_path):
    problem = 'credentials.toml: unknown provider "antropic"'
    environment = make(
        tmp_path, AiSettings(enabled=True, model=ANTHROPIC), {Provider.ANTHROPIC: "k"}, problem
    )
    status = ai_status(environment)
    assert status.credentials.issue == problem
    assert status.credentials.keys == frozenset()
    assert all(task.reason == problem and not task.ready for task in status.tasks)


def test_a_credentials_issue_does_not_hide_that_ai_is_off(tmp_path):
    environment = make(tmp_path, AiSettings(model=ANTHROPIC), issue="credentials.toml: bad")
    assert {task.reason for task in ai_status(environment).tasks} == {AI_OFF}


def test_the_status_lists_the_consents_and_the_credentials_location(tmp_path):
    environment = make(tmp_path, AiSettings())
    consent = Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW)
    environment.ai_store.grant_consent(consent)
    status = ai_status(environment)
    assert status.consents == (consent,)
    assert status.credentials.location == "/fake/config/credentials.toml"


def test_today_adds_up_only_todays_requests(tmp_path):
    environment = make(tmp_path, AiSettings(daily_token_cap=7_000))
    record(
        environment,
        call(counted=12_400, cost=0.00002),
        call(counted=100, cost=0.00001, purpose=AiTask.CHECK),
        call(counted=5_000, outcome=CallOutcome.FAILED),
        call(day=TODAY - timedelta(days=1), counted=999_999),
        call(day=TODAY + timedelta(days=1), counted=888_888),
    )
    today = ai_status(environment).today
    assert today.cap == 7_000
    assert today.counters.counted_tokens == 17_500
    assert today.counters.requests == 3
    assert today.counters.cost_usd == pytest.approx(0.00003)
    assert today.counters.requests_without_cost == 1


def test_usage_covers_the_days_oldest_first_with_the_total(tmp_path):
    environment = make(tmp_path, AiSettings(daily_token_cap=123))
    yesterday = TODAY - timedelta(days=1)
    record(
        environment,
        call(counted=300, cost=0.5),
        call(day=yesterday, counted=200),
        call(day=yesterday - timedelta(days=5), counted=9_999),
    )
    report = usage_report(environment, 2)
    assert (report.days, report.first, report.last, report.cap) == (2, yesterday, TODAY, 123)
    assert [(row.day, row.counters.counted_tokens) for row in report.rows] == [
        (yesterday, 200),
        (TODAY, 300),
    ]
    assert report.total.requests == 2
    assert report.total.counted_tokens == 500
    assert report.total.cost_usd == 0.5
    assert report.total.requests_without_cost == 1


def test_a_week_is_the_default_and_a_single_day_is_today(tmp_path):
    environment = make(tmp_path, AiSettings())
    record(environment, call(day=TODAY - timedelta(days=6)), call(day=TODAY - timedelta(days=7)))
    week = usage_report(environment)
    assert (week.days, week.first) == (7, TODAY - timedelta(days=6))
    assert week.total.requests == 1
    assert usage_report(environment, 1).first == TODAY


def test_no_requests_make_an_empty_report(tmp_path):
    report = usage_report(make(tmp_path, AiSettings()), 30)
    assert report.rows == ()
    assert report.total.requests == 0


@pytest.mark.parametrize("days", [0, -1, 367, 10_000])
def test_a_number_of_days_outside_one_to_366_is_a_usage_error(tmp_path, days):
    with pytest.raises(UsageError, match="--days must be from 1 to 366"):
        usage_report(make(tmp_path, AiSettings()), days)


def test_the_longest_report_is_366_days(tmp_path):
    report = usage_report(make(tmp_path, AiSettings()), 366)
    assert report.first == TODAY - timedelta(days=365)
