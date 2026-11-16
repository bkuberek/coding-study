"""The AI tables of progress.db (docs/specs/ai.md#records-and-progress)."""

import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from coding_study.adapters.sqlite.ai_rows import SqliteAiStore
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.ai import AiTask, Provider, Tier
from coding_study.domain.ai_models import ProviderErrorKind
from coding_study.domain.ai_records import (
    CallOutcome,
    Consent,
    ModelCall,
    ReviewItem,
    ReviewRecord,
    Verdict,
)
from coding_study.domain.attempts import AttemptMode, NewAttempt

STARTED = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
DAY = date(2026, 10, 24)
SHA = "a" * 64


@pytest.fixture
def database(tmp_path: Path) -> Path:
    return tmp_path / "progress.db"


@pytest.fixture
def store(database: Path) -> SqliteAiStore:
    return SqliteAiStore(database)


@pytest.fixture
def progress(database: Path) -> SqliteProgressStore:
    return SqliteProgressStore(database)


def attempt(progress: SqliteProgressStore, slug: str) -> int:
    started = NewAttempt(slug, None, AttemptMode.NEW, STARTED)
    return progress.add_attempt(started).id


def consent(model: str = "model-a", purpose: AiTask = AiTask.REVIEW, minutes: int = 0) -> Consent:
    return Consent(Provider.ANTHROPIC, model, purpose, STARTED + timedelta(minutes=minutes))


def call(
    minutes: int = 0, day: date = DAY, purpose: AiTask = AiTask.REVIEW, **fields: object
) -> ModelCall:
    started = STARTED + timedelta(minutes=minutes)
    values: dict[str, object] = {
        "purpose": purpose,
        "provider": Provider.OPENROUTER,
        "model": "vendor/model-b",
        "tier": Tier.FAST,
        "attempt_id": None,
        "local_day": day,
        "started_at": started,
        "ended_at": started + timedelta(seconds=3),
        "outcome": CallOutcome.OK,
        "error": None,
        "input_tokens": 1200,
        "output_tokens": 300,
        "counted_tokens": 1500,
        "cost_usd": 0.0021,
    }
    return ModelCall(**{**values, **fields})  # type: ignore[arg-type]


def review(attempt_id: int, minutes: int = 0, **fields: object) -> ReviewRecord:
    items = (
        ReviewItem(1, "Scope", "States the goal", Verdict.MET, ("one", "two"), ""),
        ReviewItem(2, "Scope", "Names the limits", Verdict.PARTIAL, ("three",), "no numbers"),
        ReviewItem(3, "Data", "Names the key", Verdict.MISSING, (), "no key"),
    )
    values: dict[str, object] = {
        "attempt_id": attempt_id,
        "created_at": STARTED + timedelta(minutes=minutes),
        "provider": Provider.GOOGLE,
        "model": "model-c",
        "prompt_version": "review-1",
        "rubric_sha256": SHA,
        "notes_sha256": "b" * 64,
        "items": items,
        "summary": "Scope is covered; the key is missing.",
        "quotes_dropped": 2,
        "input_tokens": 5000,
        "output_tokens": 800,
        "cost_usd": 0.03,
    }
    return ReviewRecord(**{**values, **fields})  # type: ignore[arg-type]


def table_names(database: Path) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {name for (name,) in rows}


# The database


def test_the_first_call_creates_the_database_with_the_three_tables(store, database):
    store.consents()
    assert {"ai_reviews", "ai_calls", "ai_consents"} <= table_names(database)


def test_an_empty_database_holds_no_rows(store):
    assert (
        store.consents(),
        store.calls_between(date.min, date.max),
        store.review(1),
        store.reviews_of_attempt(1),
        store.reviews_of_problem("two-sum"),
    ) == ((), (), None, (), ())


# Consents


def test_a_consent_reads_back_by_provider_model_and_purpose(store):
    granted = consent()
    store.grant_consent(granted)
    assert store.consent(Provider.ANTHROPIC, "model-a", AiTask.REVIEW) == granted


def test_a_consent_is_for_one_provider_model_and_purpose(store):
    store.grant_consent(consent())
    assert [
        store.consent(Provider.OPENAI, "model-a", AiTask.REVIEW),
        store.consent(Provider.ANTHROPIC, "model-b", AiTask.REVIEW),
        store.consent(Provider.ANTHROPIC, "model-a", AiTask.CHECK),
    ] == [None, None, None]


def test_granting_again_keeps_the_first_time(store):
    store.grant_consent(consent(minutes=0))
    store.grant_consent(consent(minutes=30))
    assert store.consents() == (consent(minutes=0),)


def test_consents_come_by_provider_model_and_purpose(store):
    second = Consent(Provider.GOOGLE, "model-a", AiTask.REVIEW, STARTED)
    for granted in (second, consent("model-b"), consent(purpose=AiTask.CHECK), consent()):
        store.grant_consent(granted)
    assert [(c.provider, c.model, c.purpose) for c in store.consents()] == [
        (Provider.ANTHROPIC, "model-a", AiTask.CHECK),
        (Provider.ANTHROPIC, "model-a", AiTask.REVIEW),
        (Provider.ANTHROPIC, "model-b", AiTask.REVIEW),
        (Provider.GOOGLE, "model-a", AiTask.REVIEW),
    ]


def test_a_consent_is_revoked_once(store):
    store.grant_consent(consent())
    first = store.revoke_consent(Provider.ANTHROPIC, "model-a", AiTask.REVIEW)
    second = store.revoke_consent(Provider.ANTHROPIC, "model-a", AiTask.REVIEW)
    assert (first, second, store.consents()) == (True, False, ())


def test_a_revoked_consent_can_be_granted_again_with_a_new_time(store):
    store.grant_consent(consent(minutes=0))
    store.revoke_consent(Provider.ANTHROPIC, "model-a", AiTask.REVIEW)
    store.grant_consent(consent(minutes=45))
    assert store.consents() == (consent(minutes=45),)


def test_a_time_in_another_zone_is_stored_as_the_same_instant(store):
    local = STARTED.astimezone(timezone(timedelta(hours=5)))
    store.grant_consent(replace(consent(), granted_at=local))
    (found,) = store.consents()
    assert found.granted_at == STARTED


# Requests


def test_a_request_reads_back_as_it_was_recorded(store):
    recorded = call(error=None)
    store.record_call(recorded)
    assert store.calls_between(DAY, DAY) == (recorded,)


def test_a_failed_request_keeps_its_error_and_its_missing_usage(store):
    failed = call(
        outcome=CallOutcome.FAILED,
        error=ProviderErrorKind.RATE_LIMIT,
        tier=None,
        input_tokens=None,
        output_tokens=None,
        counted_tokens=900,
        cost_usd=None,
    )
    store.record_call(failed)
    assert store.calls_between(DAY, DAY) == (failed,)


def test_a_request_of_an_attempt_keeps_the_attempt(store, progress):
    reviewed = attempt(progress, "url-shortener")
    store.record_call(call(attempt_id=reviewed))
    assert store.calls_between(DAY, DAY)[0].attempt_id == reviewed


def test_a_request_of_an_attempt_that_does_not_exist_is_refused(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.record_call(call(attempt_id=99))


def test_requests_of_the_days_asked_for_come_oldest_first(store):
    for minutes, day in ((30, DAY), (10, DAY), (5, DAY - timedelta(days=1))):
        store.record_call(call(minutes, day))
    store.record_call(call(1, DAY + timedelta(days=1)))
    found = store.calls_between(DAY - timedelta(days=1), DAY)
    assert [c.started_at for c in found] == [
        STARTED + timedelta(minutes=5),
        STARTED + timedelta(minutes=10),
        STARTED + timedelta(minutes=30),
    ]


def test_both_days_of_the_range_are_included(store):
    for offset in range(-1, 4):
        store.record_call(call(offset + 5, DAY + timedelta(days=offset)))
    found = store.calls_between(DAY, DAY + timedelta(days=2))
    assert [c.local_day for c in found] == [DAY + timedelta(days=n) for n in range(3)]


def test_a_request_counts_in_the_local_day_recorded_not_the_day_of_its_time(store):
    next_day = DAY + timedelta(days=1)
    store.record_call(call(0, next_day, started_at=STARTED.replace(hour=23, minute=59)))
    assert (len(store.calls_between(DAY, DAY)), len(store.calls_between(next_day, next_day))) == (
        0,
        1,
    )


def test_a_request_with_an_outcome_other_than_the_three_is_refused(store, database):
    store.consents()
    with closing(sqlite3.connect(database)) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO ai_calls (purpose, provider, model, local_day, started_at, ended_at, "
            "outcome, counted_tokens) VALUES ('review', 'openai', 'm', '2026-10-24', 'a', 'b', "
            "'lost', 1)"
        )


# Reviews


def test_a_review_reads_back_as_it_was_added(store, progress):
    reviewed = attempt(progress, "url-shortener")
    added = review(reviewed)
    review_id = store.add_review(added)
    assert store.review(review_id) == replace(added, id=review_id)


def test_a_review_without_usage_or_cost_keeps_them_null(store, progress):
    reviewed = attempt(progress, "url-shortener")
    bare = review(reviewed, input_tokens=None, output_tokens=None, cost_usd=None)
    assert store.review(store.add_review(bare)) == replace(bare, id=1)


def test_a_review_keeps_the_format_and_its_dismissal(store, progress):
    reviewed = attempt(progress, "url-shortener")
    dismissed = review(reviewed, dismissed_at=STARTED + timedelta(days=1))
    assert store.review(store.add_review(dismissed)) == replace(dismissed, id=1)


def test_review_ids_rise(store, progress):
    reviewed = attempt(progress, "url-shortener")
    assert [store.add_review(review(reviewed)) for _ in range(3)] == [1, 2, 3]


def test_a_review_of_an_attempt_that_does_not_exist_is_refused(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.add_review(review(99))


def test_the_items_keep_their_order_and_their_quotes(store, progress):
    reviewed = attempt(progress, "url-shortener")
    found = store.review(store.add_review(review(reviewed)))
    assert found is not None
    assert [(item.number, item.verdict, item.evidence) for item in found.items] == [
        (1, Verdict.MET, ("one", "two")),
        (2, Verdict.PARTIAL, ("three",)),
        (3, Verdict.MISSING, ()),
    ]


def test_a_quote_with_text_json_escapes_reads_back_whole(store, progress):
    reviewed = attempt(progress, "url-shortener")
    quote = 'say "hi"\nthen \\ done é 中'
    item = ReviewItem(1, "Scope", "Says hi", Verdict.MET, (quote,), "")
    found = store.review(store.add_review(review(reviewed, items=(item,))))
    assert found is not None
    assert found.items[0].evidence == (quote,)


def test_the_reviews_of_an_attempt_come_newest_first_and_only_its_own(store, progress):
    one, other = attempt(progress, "url-shortener"), attempt(progress, "rate-limiter")
    first = store.add_review(review(one, minutes=0))
    store.add_review(review(other, minutes=5))
    second = store.add_review(review(one, minutes=10))
    assert [r.id for r in store.reviews_of_attempt(one)] == [second, first]


def test_reviews_made_in_the_same_second_come_the_later_id_first(store, progress):
    reviewed = attempt(progress, "url-shortener")
    ids = [store.add_review(review(reviewed)) for _ in range(3)]
    assert [r.id for r in store.reviews_of_attempt(reviewed)] == ids[::-1]


def test_the_reviews_of_a_problem_span_its_attempts_newest_first(store, progress):
    first_attempt = attempt(progress, "url-shortener")
    second_attempt = attempt(progress, "url-shortener")
    other = attempt(progress, "rate-limiter")
    a = store.add_review(review(first_attempt, minutes=0))
    store.add_review(review(other, minutes=5))
    b = store.add_review(review(second_attempt, minutes=10))
    assert [r.id for r in store.reviews_of_problem("url-shortener")] == [b, a]
    assert [r.id for r in store.reviews_of_problem("rate-limiter")] == [2]


def test_a_problem_without_reviews_has_none(store, progress):
    store.add_review(review(attempt(progress, "url-shortener")))
    assert store.reviews_of_problem("rate-limiter") == ()


def test_dismissed_reviews_stay_in_the_lists(store, progress):
    reviewed = attempt(progress, "url-shortener")
    review_id = store.add_review(review(reviewed))
    store.dismiss_review(review_id, STARTED + timedelta(hours=1))
    assert [r.dismissed_at for r in store.reviews_of_problem("url-shortener")] == [
        STARTED + timedelta(hours=1)
    ]
    assert len(store.reviews_of_attempt(reviewed)) == 1


def test_a_review_is_dismissed_once_and_the_first_time_stays(store, progress):
    review_id = store.add_review(review(attempt(progress, "url-shortener")))
    first = store.dismiss_review(review_id, STARTED + timedelta(hours=1))
    second = store.dismiss_review(review_id, STARTED + timedelta(hours=2))
    found = store.review(review_id)
    assert (first, second) == (True, False)
    assert found is not None
    assert found.dismissed_at == STARTED + timedelta(hours=1)


def test_dismissing_a_review_that_is_not_there_changes_nothing(store):
    assert store.dismiss_review(7, STARTED) is False


# Beside the progress store


def test_the_progress_store_and_this_one_share_the_database(store, progress):
    reviewed = attempt(progress, "url-shortener")
    store.add_review(review(reviewed))
    assert progress.snapshot().row_counts()["ai_reviews"] == 1


def test_a_clear_empties_the_three_tables(store, progress):
    reviewed = attempt(progress, "url-shortener")
    store.add_review(review(reviewed))
    store.record_call(call(attempt_id=reviewed))
    store.grant_consent(consent())
    progress.clear()
    assert (store.reviews_of_attempt(reviewed), store.calls_between(date.min, date.max)) == ((), ())
    assert store.consents() == ()


def test_the_snapshot_holds_the_reviews_but_not_the_requests_or_consents(store, progress):
    reviewed = attempt(progress, "url-shortener")
    store.add_review(review(reviewed))
    store.record_call(call())
    store.grant_consent(consent())
    tables = progress.snapshot().tables
    assert (len(tables["ai_reviews"]), "ai_calls" in tables, "ai_consents" in tables) == (
        1,
        False,
        False,
    )


def test_a_restore_puts_the_reviews_back_and_leaves_the_requests_and_consents(
    store, progress, tmp_path
):
    reviewed = attempt(progress, "url-shortener")
    store.add_review(review(reviewed))
    snapshot = progress.snapshot()
    other = SqliteProgressStore(tmp_path / "other" / "progress.db")
    other_store = SqliteAiStore(tmp_path / "other" / "progress.db")
    other_store.grant_consent(consent())
    other_store.record_call(call())
    other.restore(snapshot)
    assert (
        len(other_store.reviews_of_attempt(reviewed)),
        len(other_store.consents()),
        len(other_store.calls_between(date.min, date.max)),
    ) == (1, 1, 1)
