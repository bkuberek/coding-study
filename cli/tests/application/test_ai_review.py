"""AI review of a rubric problem's notes: its refusals in the spec's order, the dry run, the stored
record, and list, show, dismiss and `notes_changed` (docs/specs/ai.md#ai-review), over fakes of
the model, the credentials and the clock."""

import hashlib
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.ai_consent import RefusingAsker
from coding_study.application.ai_review import (
    MAX_NOTES_BYTES,
    Reviewed,
    dismiss_review,
    dry_run_review,
    list_reviews,
    plan_review,
    prepare_review,
    run_review,
    show_review,
)
from coding_study.application.ai_send import ConsentQuestion, NotSent
from coding_study.application.attempt_status import attempt_status
from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.show_stats import StatsRequest, show_stats
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.ai import AI_OFF, AiTask, ModelRef, Provider
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from coding_study.domain.ai_records import CallOutcome, Consent, Verdict
from coding_study.domain.ai_review import INSTRUCTIONS, REVIEW_SCHEMA
from coding_study.domain.ai_routing import Target
from coding_study.domain.ai_usage import estimate_input_tokens
from coding_study.domain.attempts import AttemptMode, NewAttempt, Rating
from coding_study.domain.config import AiSettings, Config
from coding_study.domain.errors import UnknownProblemError, UsageError
from coding_study.domain.problem import Language
from coding_study.entrypoints.commands.stats import stats_document
from tests.fakes import (
    NOW,
    FakeAiStore,
    FakeClock,
    FakeCredentials,
    ScriptedLanguageModels,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
NOTES = "notes/system-design/url-shortener.md"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
SECRET = "sk-sentinel-0123456789"
USAGE = Usage(9_812, 2_410)
CRITERIA = 5
"""url-shortener's rubric: two criteria, two, one."""
ANSWER = "## Requirements\n\nRedirects stay fast even when creating links is down.\n"
TEMPLATE_ONLY_MESSAGE = "your notes are still the template: write your answer in {path} first"


class Asker:
    def __init__(self, answer: bool = True) -> None:
        self.answer = answer
        self.questions: list[ConsentQuestion] = []

    def ask(self, question: ConsentQuestion) -> bool:
        self.questions.append(question)
        return self.answer


def reply(
    verdict: str = "met", evidence: tuple[str, ...] = (), count: int = CRITERIA
) -> ModelReply:
    data = {
        "criteria": [
            {
                "id": f"C{number}",
                "verdict": verdict,
                "evidence": list(evidence),
                "gaps": "" if verdict == "met" else "nothing on this",
            }
            for number in range(1, count + 1)
        ],
        "summary": "Strong on the redirect path.",
    }
    return ModelReply(Ending.COMPLETE, "{}", data, USAGE)


GOOD = reply(evidence=("redirects stay fast",))


def build(tmp_path: Path, *answers: ModelReply | ProviderError, **overrides: object) -> Environment:
    parts: dict[str, object] = {
        "config": Config(ai=AiSettings(enabled=True, model=ANTHROPIC)),
        "credentials": FakeCredentials({Provider.ANTHROPIC: SECRET}),
        "models": ScriptedLanguageModels(*answers),
        "clock": FakeClock(),
    }
    parts.update(overrides)
    root = repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS)
    return make_environment(root, **parts)


def start(environment: Environment, slug: str = "url-shortener", **fields: object):
    return start_item_attempt(environment, ItemStartRequest(slug, **fields)).attempt  # type: ignore[arg-type]


def answered(environment: Environment, text: str = ANSWER) -> None:
    environment.workspace.write_text(NOTES, text)


def started(tmp_path: Path, *answers: ModelReply | ProviderError, **overrides: object):
    """An environment with an attempt of url-shortener in progress and its notes written."""
    environment = build(tmp_path, *answers, **overrides)
    start(environment)
    answered(environment)
    return environment


def review(
    environment: Environment, asker: Asker | None = None, slug: str | None = "url-shortener"
):
    prepared = prepare_review(environment, slug)
    return run_review(environment, prepared, asker or Asker())


def reviewed(environment: Environment, asker: Asker | None = None) -> Reviewed:
    result = review(environment, asker)
    assert isinstance(result, Reviewed)
    return result


def requests(environment: Environment):
    models = environment.models
    assert isinstance(models, ScriptedLanguageModels)
    return models.requests


def nothing_happened(environment: Environment) -> None:
    store = environment.ai_store
    assert store.calls_between(NOW.date(), NOW.date() + timedelta(days=30)) == ()
    assert store.consents() == ()
    assert store.reviews_of_problem("url-shortener") == ()
    assert requests(environment) == []


# refusals, in the spec's order


def test_a_problem_checked_by_tests_is_not_reviewed(tmp_path):
    environment = build(tmp_path)
    with pytest.raises(UsageError) as refused:
        plan_review(environment, "two-sum")
    assert str(refused.value) == (
        "two-sum is checked by tests; AI review is for rubric problems "
        "(system-design and code-review)"
    )


def test_an_unknown_problem_is_unknown(tmp_path):
    with pytest.raises(UnknownProblemError):
        plan_review(build(tmp_path), "no-such-problem")


def test_a_problem_without_an_attempt_says_how_to_start_one(tmp_path):
    with pytest.raises(UsageError) as refused:
        plan_review(build(tmp_path), "url-shortener")
    assert str(refused.value) == (
        "no attempt of url-shortener yet: start it with cstudy start url-shortener"
    )


def test_without_a_slug_the_active_attempt_names_the_problem(tmp_path):
    environment = started(tmp_path)
    plan = plan_review(environment, None)
    assert (plan.meta.slug, plan.attempt.id) == ("url-shortener", 1)


def test_without_a_slug_and_without_an_attempt_nothing_is_named(tmp_path):
    with pytest.raises(UsageError, match="no attempt in progress; start one with cstudy start"):
        plan_review(build(tmp_path), None)


def test_without_a_slug_an_attempt_at_a_problem_checked_by_tests_is_refused(tmp_path):
    environment = build(tmp_path)
    environment.progress.add_attempt(
        NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW, None, "python/practice/x.py")
    )
    with pytest.raises(UsageError, match="two-sum is checked by tests"):
        plan_review(environment, None)


def test_missing_notes_are_refused(tmp_path):
    environment = build(tmp_path)
    start(environment)
    (tmp_path / NOTES).unlink()
    with pytest.raises(UsageError) as refused:
        plan_review(environment, "url-shortener")
    assert str(refused.value) == f"{NOTES} is missing: AI review reads your notes"


def test_the_template_as_started_is_refused(tmp_path):
    environment = build(tmp_path)
    start(environment)
    with pytest.raises(UsageError) as refused:
        plan_review(environment, "url-shortener")
    assert str(refused.value) == TEMPLATE_ONLY_MESSAGE.format(path=NOTES)


@pytest.mark.parametrize(
    "notes",
    [
        "",
        "   \n\n\t\n",
        "# Title\n\n## Requirements\n\n###### Deep\n",
        "<!-- a comment -->\n",
        "<!-- a comment\nover two lines\n-->\n## Design\n<!-- another -->   \n",
        "#\n##\n",
    ],
)
def test_notes_with_nothing_but_comments_headings_and_blank_space_are_refused(tmp_path, notes):
    environment = started(tmp_path)
    answered(environment, notes)
    with pytest.raises(UsageError, match="your notes are still the template"):
        plan_review(environment, "url-shortener")


@pytest.mark.parametrize(
    "notes", ["one line of answer", "## Design\n\n#hashtag\n", "<!-- note -->\n\n- a bullet\n"]
)
def test_any_text_beyond_comments_and_headings_is_an_answer(tmp_path, notes):
    environment = started(tmp_path)
    answered(environment, notes)
    assert plan_review(environment, "url-shortener").notes == notes


def test_notes_over_64_kib_are_refused_and_exactly_64_kib_are_read(tmp_path):
    environment = started(tmp_path)
    answered(environment, "a" * MAX_NOTES_BYTES)
    assert plan_review(environment, "url-shortener").notes_path == NOTES
    answered(environment, "a" * (80 * 1024))
    with pytest.raises(UsageError) as refused:
        plan_review(environment, "url-shortener")
    assert str(refused.value) == "your notes are 80 KiB; AI review reads at most 64 KiB"


def test_notes_a_byte_over_the_limit_round_up(tmp_path):
    environment = started(tmp_path)
    answered(environment, "a" * (MAX_NOTES_BYTES + 1))
    with pytest.raises(UsageError, match="your notes are 65 KiB; AI review reads at most 64 KiB"):
        plan_review(environment, "url-shortener")


def test_size_counts_bytes_not_characters(tmp_path):
    environment = started(tmp_path)
    answered(environment, "é" * (MAX_NOTES_BYTES // 2 + 1))
    with pytest.raises(UsageError, match="your notes are 65 KiB"):
        plan_review(environment, "url-shortener")


def test_a_running_mock_locks_the_review(tmp_path):
    environment = started(tmp_path)
    start(environment, "news-feed", mock=True, timer_s=2_000)
    environment.clock.advance(timedelta(seconds=140))  # type: ignore[attr-defined]
    with pytest.raises(UsageError) as refused:
        plan_review(environment, "url-shortener")
    assert str(refused.value) == (
        "cstudy ai review is locked during the mock interview (news-feed; 31:00 left); it "
        "unlocks when the timer ends or every problem is done"
    )


def test_a_mock_that_ended_no_longer_locks(tmp_path):
    environment = started(tmp_path)
    start(environment, "news-feed", mock=True, timer_s=600)
    environment.clock.advance(timedelta(seconds=601))  # type: ignore[attr-defined]
    assert plan_review(environment, "url-shortener").meta.slug == "url-shortener"


def test_the_dry_run_is_locked_by_a_mock_too(tmp_path):
    environment = started(tmp_path)
    start(environment, "news-feed", mock=True, timer_s=2_000)
    with pytest.raises(UsageError, match="locked during the mock interview"):
        dry_run_review(environment, "url-shortener")


def test_the_notes_refusals_come_before_the_mock_lock(tmp_path):
    environment = build(tmp_path)
    start(environment)
    start(environment, "news-feed", mock=True, timer_s=2_000)
    with pytest.raises(UsageError, match="still the template"):
        plan_review(environment, "url-shortener")


def test_the_mock_lock_comes_before_ai_off(tmp_path):
    environment = started(tmp_path, config=Config())
    start(environment, "news-feed", mock=True, timer_s=2_000)
    with pytest.raises(UsageError, match="locked during the mock interview"):
        prepare_review(environment, "url-shortener")


def test_the_notes_refusals_come_before_ai_off(tmp_path):
    environment = build(tmp_path, config=Config())
    with pytest.raises(UsageError, match="no attempt of url-shortener yet"):
        prepare_review(environment, "url-shortener")


def test_ai_off_refuses_a_review(tmp_path):
    environment = started(tmp_path, config=Config())
    with pytest.raises(UsageError) as refused:
        prepare_review(environment, "url-shortener")
    assert str(refused.value) == AI_OFF
    nothing_happened(environment)


def test_an_unset_model_refuses_a_review(tmp_path):
    environment = started(tmp_path, config=Config(ai=AiSettings(enabled=True)))
    with pytest.raises(
        UsageError, match=r"^ai\.model is not set: choose the model of fixed routing"
    ):
        prepare_review(environment, "url-shortener")


def test_a_provider_without_a_key_refuses_a_review(tmp_path):
    environment = started(tmp_path, credentials=FakeCredentials())
    with pytest.raises(UsageError) as refused:
        prepare_review(environment, "url-shortener")
    assert str(refused.value) == (
        "no key for anthropic, which ai.model uses: cstudy ai key anthropic, or Settings"
    )


# the attempt reviewed


def test_a_finished_attempt_is_reviewed_when_none_is_in_progress(tmp_path):
    environment = started(tmp_path, GOOD)
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    result = reviewed(environment)
    assert result.review.record.attempt_id == 1


def test_the_attempt_in_progress_is_reviewed_before_an_earlier_one(tmp_path):
    environment = started(tmp_path, GOOD)
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    second = start(environment)
    answered(environment)
    assert plan_review(environment, "url-shortener").attempt.id == second.id


# the dry run


def test_the_dry_run_sends_nothing_and_records_nothing(tmp_path):
    environment = started(tmp_path)
    dry = dry_run_review(environment, "url-shortener")
    assert dry.plan.payload.instructions == INSTRUCTIONS
    assert ANSWER in dry.plan.payload.message
    assert "C1. Separates the write path (create) from the read path (redirect)" in (
        dry.plan.payload.message
    )
    nothing_happened(environment)


def test_the_dry_run_needs_no_key_no_consent_and_not_even_ai_on(tmp_path):
    environment = started(tmp_path, config=Config(), credentials=FakeCredentials())
    dry = dry_run_review(environment, "url-shortener")
    assert (dry.targets, dry.unset) == (
        (),
        "ai.model is not set: choose the model of fixed "
        "routing in Settings or with cstudy config edit",
    )
    nothing_happened(environment)


def test_the_dry_run_names_the_model_and_estimates_the_input(tmp_path):
    environment = started(tmp_path, config=Config(), credentials=FakeCredentials())
    configured = replace(environment, config=Config(ai=AiSettings(enabled=False, model=ANTHROPIC)))
    dry = dry_run_review(configured, "url-shortener")
    assert dry.targets == (Target(None, ANTHROPIC),)
    assert dry.unset is None
    assert dry.input_tokens == estimate_input_tokens(dry.plan.payload.text)
    assert dry.max_output_tokens == 16_000


def test_the_dry_run_text_is_the_text_a_review_sends(tmp_path):
    environment = started(tmp_path, GOOD)
    dry = dry_run_review(environment, "url-shortener")
    reviewed(environment)
    (request,) = requests(environment)
    assert (request.instructions, request.message) == (
        dry.plan.payload.instructions,
        dry.plan.payload.message,
    )


def test_a_review_sends_the_exercise_the_rubric_and_the_notes_only(tmp_path):
    environment = started(tmp_path)
    message = plan_review(environment, "url-shortener").payload.message
    template = (tmp_path / "problems/url-shortener/template.md").read_text()
    assert "# Exercise: URL Shortener" in message
    assert "100 redirects for every link created" in message
    assert "Create, redirect and expire links" not in message
    assert "6 billion links over five years" not in message
    assert template.strip() not in message
    assert str(tmp_path) not in message


def test_a_code_review_sends_its_change(tmp_path):
    environment = build(tmp_path)
    start(environment, "retry-wrapper")
    environment.workspace.write_text(
        "notes/code-review/retry-wrapper.md", "The retry swallows every exception.\n"
    )
    plan = plan_review(environment, "retry-wrapper")
    assert "```diff\n--- a/payments/client.py" in plan.payload.message
    assert [item.name for item in plan.payload.items] == [
        "instructions review-1",
        "prompt.md",
        "change.diff",
        "rubric.md, 3 criteria",
        "your notes",
    ]


def test_the_items_list_what_is_sent_with_sizes(tmp_path):
    environment = started(tmp_path)
    items = plan_review(environment, "url-shortener").payload.items
    assert [(item.name, item.detail) for item in items] == [
        ("instructions review-1", ""),
        ("prompt.md", ""),
        (f"rubric.md, {CRITERIA} criteria", ""),
        ("your notes", NOTES),
    ]
    assert items[0].size_bytes == len(INSTRUCTIONS.encode())
    assert items[-1].size_bytes == len(ANSWER.encode())


# a review


def test_a_good_reply_is_stored_as_a_review(tmp_path):
    environment = started(tmp_path, GOOD)
    asker = Asker()
    result = reviewed(environment, asker)
    record = result.review.record
    rubric = (tmp_path / "problems/url-shortener/rubric.md").read_bytes()
    assert (record.id, record.attempt_id, record.created_at) == (1, 1, NOW)
    assert (record.provider, record.model, record.prompt_version) == (
        Provider.ANTHROPIC,
        "claude-x",
        "review-1",
    )
    assert record.rubric_sha256 == hashlib.sha256(rubric).hexdigest()
    assert record.notes_sha256 == hashlib.sha256(ANSWER.encode()).hexdigest()
    assert [item.number for item in record.items] == [1, 2, 3, 4, 5]
    assert record.items[0].evidence == ("redirects stay fast",)
    assert record.summary == "Strong on the redirect path."
    assert (record.input_tokens, record.output_tokens, record.cost_usd) == (9_812, 2_410, None)
    assert (result.review.slug, result.review.notes_changed) == ("url-shortener", False)
    assert environment.ai_store.review(1) == record


def test_the_request_asks_for_the_review_schema(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    (request,) = requests(environment)
    assert (request.model, request.schema, request.schema_name) == (
        ANTHROPIC,
        REVIEW_SCHEMA,
        "review",
    )
    assert (request.max_output_tokens, request.deadline_s) == (16_000, 300)


def test_the_request_row_belongs_to_the_attempt(tmp_path):
    environment = started(tmp_path, GOOD)
    result = reviewed(environment)
    (call,) = environment.ai_store.calls_between(NOW.date(), NOW.date())
    assert result.call == call
    assert (call.purpose, call.attempt_id, call.outcome) == (AiTask.REVIEW, 1, CallOutcome.OK)


def test_the_first_review_asks_for_consent_and_records_it(tmp_path):
    environment = started(tmp_path, GOOD, GOOD)
    asker = Asker()
    reviewed(environment, asker)
    reviewed(environment, asker)
    (question,) = asker.questions
    assert [item.name for item in question.items][-1] == "your notes"
    (consent,) = environment.ai_store.consents()
    assert (consent.provider, consent.model, consent.purpose) == (
        Provider.ANTHROPIC,
        "claude-x",
        AiTask.REVIEW,
    )


def test_a_no_at_the_question_sends_and_records_nothing(tmp_path):
    environment = started(tmp_path)
    result = review(environment, Asker(answer=False))
    assert result == NotSent(Target(None, ANTHROPIC))
    nothing_happened(environment)


def test_without_a_terminal_a_missing_consent_refuses(tmp_path):
    environment = started(tmp_path)
    prepared = prepare_review(environment, "url-shortener")
    with pytest.raises(UsageError, match=r"^AI review needs your consent to send to anthropic"):
        run_review(environment, prepared, RefusingAsker())
    nothing_happened(environment)


def test_a_recorded_consent_asks_nothing(tmp_path):
    environment = started(tmp_path, GOOD)
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    assert isinstance(
        run_review(environment, prepare_review(environment, "url-shortener"), RefusingAsker()),
        Reviewed,
    )


def test_quotes_the_notes_do_not_hold_are_dropped_and_counted(tmp_path):
    reply_with_invented_quote = reply(evidence=("redirects stay fast", "an invented sentence"))
    environment = started(tmp_path, reply_with_invented_quote)
    record = reviewed(environment).review.record
    assert record.items[0].evidence == ("redirects stay fast",)
    assert record.quotes_dropped == CRITERIA


def test_a_reply_that_fails_its_checks_stores_no_review_and_a_failed_row(tmp_path):
    environment = started(tmp_path, reply(count=CRITERIA - 1))
    with pytest.raises(ProviderError) as failed:
        review(environment)
    assert failed.value.kind is ProviderErrorKind.INVALID_REPLY
    assert "C5 missing" in str(failed.value)
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()
    (call,) = environment.ai_store.calls_between(NOW.date(), NOW.date())
    assert (call.outcome, call.error, call.counted_tokens) == (
        CallOutcome.FAILED,
        ProviderErrorKind.INVALID_REPLY,
        USAGE.total_tokens,
    )


def test_a_reply_that_is_not_an_object_stores_no_review(tmp_path):
    environment = started(tmp_path, ModelReply(Ending.COMPLETE, "plain text", None, USAGE))
    with pytest.raises(ProviderError) as failed:
        review(environment)
    assert failed.value.kind is ProviderErrorKind.INVALID_REPLY
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


@pytest.mark.parametrize("ending", [Ending.LENGTH, Ending.REFUSED])
def test_a_reply_that_ends_early_stores_no_review(tmp_path, ending):
    environment = started(tmp_path, ModelReply(ending, "", None, USAGE))
    with pytest.raises(ProviderError):
        review(environment)
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


def test_a_provider_error_stores_no_review(tmp_path):
    environment = started(tmp_path, ProviderError(ProviderErrorKind.TIMEOUT, "timed out"))
    with pytest.raises(ProviderError):
        review(environment)
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


def test_the_key_is_in_no_stored_record(tmp_path):
    environment = started(tmp_path, GOOD)
    result = reviewed(environment)
    assert SECRET not in repr(result)


# list, show, dismiss


def two_reviews(tmp_path: Path) -> Environment:
    environment = started(tmp_path, GOOD, reply("partial"))
    reviewed(environment)
    environment.clock.advance(timedelta(minutes=5))  # type: ignore[attr-defined]
    reviewed(environment)
    return environment


def test_reviews_list_newest_first(tmp_path):
    listed = list_reviews(two_reviews(tmp_path), "url-shortener")
    assert listed.slug == "url-shortener"
    assert [view.record.id for view in listed.reviews] == [2, 1]
    assert [view.record.items[0].verdict for view in listed.reviews] == [
        Verdict.PARTIAL,
        Verdict.MET,
    ]


def test_no_reviews_list_as_empty(tmp_path):
    environment = started(tmp_path)
    assert list_reviews(environment, "url-shortener").reviews == ()


def test_a_listing_holds_only_its_problems_reviews(tmp_path):
    environment = two_reviews(tmp_path)
    start(environment, "news-feed")
    assert list_reviews(environment, "news-feed").reviews == ()


def test_the_list_defaults_to_the_active_attempts_problem(tmp_path):
    environment = two_reviews(tmp_path)
    assert list_reviews(environment, None).slug == "url-shortener"


def test_a_problem_checked_by_tests_has_no_list(tmp_path):
    with pytest.raises(UsageError, match="two-sum is checked by tests"):
        list_reviews(build(tmp_path), "two-sum")


def test_a_review_shows_by_its_id(tmp_path):
    environment = two_reviews(tmp_path)
    shown = show_review(environment, 1)
    assert (shown.slug, shown.record.id, shown.notes_changed) == ("url-shortener", 1, False)


def test_an_unknown_review_id_is_refused(tmp_path):
    environment = started(tmp_path)
    for action in (show_review, dismiss_review):
        with pytest.raises(UsageError) as refused:
            action(environment, 7)
        assert str(refused.value) == "no AI review 7"


def test_dismissing_marks_the_review_and_keeps_it(tmp_path):
    environment = two_reviews(tmp_path)
    environment.clock.advance(timedelta(hours=1))  # type: ignore[attr-defined]
    done = dismiss_review(environment, 1)
    assert done.already_dismissed is False
    assert done.review.record.dismissed_at == environment.clock.now()
    listed = list_reviews(environment, "url-shortener")
    assert [(view.record.id, view.record.dismissed_at is not None) for view in listed.reviews] == [
        (2, False),
        (1, True),
    ]


def test_dismissing_again_changes_nothing(tmp_path):
    environment = two_reviews(tmp_path)
    first = dismiss_review(environment, 1).review.record.dismissed_at
    environment.clock.advance(timedelta(hours=1))  # type: ignore[attr-defined]
    again = dismiss_review(environment, 1)
    assert again.already_dismissed is True
    assert again.review.record.dismissed_at == first


def test_list_show_and_dismiss_work_with_ai_off_and_during_a_mock(tmp_path):
    environment = two_reviews(tmp_path)
    start(environment, "news-feed", mock=True, timer_s=2_000)
    quiet = replace(environment, config=Config(), credentials=FakeCredentials())
    assert len(list_reviews(quiet, "url-shortener").reviews) == 2
    assert show_review(quiet, 1).record.id == 1
    assert dismiss_review(quiet, 1).already_dismissed is False


def test_the_fake_store_dismisses_an_unknown_id_as_the_real_one_does():
    assert FakeAiStore().dismiss_review(3, NOW) is False


# notes_changed


def test_notes_are_unchanged_after_a_review(tmp_path):
    environment = started(tmp_path, GOOD)
    assert reviewed(environment).review.notes_changed is False


def test_edited_notes_are_changed(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    answered(environment, f"{ANSWER}\nMore.\n")
    assert show_review(environment, 1).notes_changed is True


def test_notes_edited_back_are_unchanged_again(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    answered(environment, "other")
    answered(environment)
    assert show_review(environment, 1).notes_changed is False


def test_notes_that_are_gone_are_null(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    (tmp_path / NOTES).unlink()
    assert show_review(environment, 1).notes_changed is None


def test_the_listing_carries_notes_changed_for_each_review(tmp_path):
    environment = two_reviews(tmp_path)
    answered(environment, "rewritten")
    listed = list_reviews(environment, "url-shortener")
    assert [view.notes_changed for view in listed.reviews] == [True, True]


def test_notes_a_later_attempt_archived_are_read_from_the_archive(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    start(environment)
    answered(environment, "the second attempt's answer")
    assert show_review(environment, 1).notes_changed is False


def test_archived_notes_edited_since_are_changed(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    start(environment)
    (archived,) = tmp_path.glob(".archive/url-shortener/1-notes/url-shortener.md")
    archived.write_text("edited in the archive")
    assert show_review(environment, 1).notes_changed is True


def test_notes_of_a_finished_attempt_are_read_where_they_were_left(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    assert show_review(environment, 1).notes_changed is False
    answered(environment, "changed after done")
    assert show_review(environment, 1).notes_changed is True


# a review changes nothing else


def standing_after_finishing(root: Path, *answers: ModelReply) -> dict[str, object]:
    """Everything a finished attempt of url-shortener leaves that a review must not touch."""
    root.mkdir()
    environment = started(root, *answers)
    if answers:
        reviewed(environment)
    status = attempt_status(environment, "url-shortener", None)
    finished = complete_attempt(environment, DoneRequest(rating=Rating.OK))
    progress = environment.progress
    return {
        "status": status,
        "attempt": finished.attempt,
        "grade": finished.attempt.grade,
        "schedule": finished.schedule,
        "stored schedule": progress.schedule_entry("url-shortener"),
        "attempts": progress.finished_attempts(),
        "progress": progress.problem_progress(),
        "stats": stats_document(show_stats(environment, StatsRequest())),
    }


def test_a_stored_review_changes_no_grade_schedule_or_stats(tmp_path):
    without = standing_after_finishing(tmp_path / "without")
    with_review = standing_after_finishing(tmp_path / "with", GOOD)
    assert with_review == without
    assert without["grade"] is not None
    assert without["stored schedule"] is not None


def test_the_review_of_the_comparison_is_stored(tmp_path):
    environment = started(tmp_path, GOOD)
    reviewed(environment)
    assert len(environment.ai_store.reviews_of_problem("url-shortener")) == 1
