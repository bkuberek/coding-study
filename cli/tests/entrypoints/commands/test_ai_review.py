"""`cstudy ai review` (docs/specs/cli.md#cstudy-ai-review): a review, its dry run, the list, show
and dismiss of stored reviews, `--json`, the exit codes and the consent question. Requests go to
the fake provider (`tests/fake_ai_provider.py`) through the real Anthropic adapter."""

import json
import re
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.ai.http_json import ENDPOINT_VARIABLE
from coding_study.adapters.ai.models import open_language_models
from coding_study.application.ai_review import dry_run_review
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.ai import AiTask, ModelRef, Provider
from coding_study.domain.ai_records import ReviewItem, ReviewRecord, Verdict
from coding_study.domain.ai_review import INSTRUCTIONS
from coding_study.domain.config import AiSettings, Config
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import ai_consent_prompt, ai_review
from coding_study.entrypoints.shared import ExitCode
from tests.fake_ai_provider import Answer, FakeAiProvider, Route
from tests.fakes import (
    NOW,
    FakeClock,
    FakeCredentials,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
NOTES = "notes/system-design/url-shortener.md"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
SECRET = "sk-sentinel-0123456789"
ANSWER = "## Requirements\n\nRedirects stay fast even when creating links is down.\n"
CRITERIA = 5
ESCAPE = "\x1b"
runner = CliRunner()


@pytest.fixture
def provider() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as fake:
        yield fake
    assert fake.unanswered == []


def complete(verdicts, evidence=(), gaps="nothing on this", summary="Strong on the redirect path."):
    """The Anthropic reply that carries a review: `verdicts` are the verdicts of C1 to Cn."""
    review = {
        "criteria": [
            {
                "id": f"C{number}",
                "verdict": verdict,
                "evidence": list(evidence) if number == 1 else [],
                "gaps": "" if verdict == "met" else gaps,
            }
            for number, verdict in enumerate(verdicts, start=1)
        ],
        "summary": summary,
    }
    return Answer(
        json={
            "content": [{"type": "text", "text": json.dumps(review)}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 9_812, "output_tokens": 2_410},
        }
    )


GOOD = complete(["met", "partial", "missing", "met", "partial"], evidence=("redirects stay fast",))


def make(tmp_path, provider, *, notes: str | None = ANSWER, settings=None, keys=True, consent=True):
    """An environment whose models are the real adapters over the fake provider, with an attempt
    at url-shortener in progress."""
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS),
        config=Config(ai=settings or AiSettings(enabled=True, model=ANTHROPIC)),
        credentials=FakeCredentials({Provider.ANTHROPIC: SECRET} if keys else {}),
        models=open_language_models({ENDPOINT_VARIABLE: provider.endpoint}),
        clock=FakeClock(),
    )
    start_item_attempt(environment, ItemStartRequest("url-shortener"))
    if notes is not None:
        environment.workspace.write_text(NOTES, notes)
    if consent:
        grant(environment)
    return environment


def grant(environment) -> None:
    from coding_study.domain.ai_records import Consent

    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))


def invoke(monkeypatch, environment, *arguments: str, input=None):
    monkeypatch.setattr(ai_review, "load_environment", lambda *_: environment)
    return runner.invoke(cli.app, ["ai", "review", *arguments], input=input)


def reviewed(monkeypatch, provider, environment, *arguments: str):
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, GOOD)
    result = invoke(monkeypatch, environment, *arguments)
    assert result.exit_code == ExitCode.SUCCESS, result.stderr
    return result


def dismissed(environment):
    record = environment.ai_store.review(1)
    assert record is not None
    return record.dismissed_at


def sent(provider) -> list:
    return provider.requests_to(Provider.ANTHROPIC, Route.COMPLETE)


# a review

REVIEW_OUTPUT = [
    "AI review · url-shortener · attempt 1 · anthropic:claude-x · review-1",
    "The same answer can get a different review. It changes no grade and no schedule.",
    "",
    "Requirements and estimates",
    "  met      Separates the write path (create) from the read path (redirect) and notes the "
    "100:1 ratio.",
    '           "redirects stay fast"',
    "  partly   Estimates storage for five years of links.",
    "           gap: nothing on this",
    "",
    "Design",
    "  missed   Picks a key scheme (counter with base62, hash with collision handling, or "
    "pre-generated keys) and explains the trade-off.",
    "           gap: nothing on this",
    "  met      Caches hot links in front of the store.",
    "",
    "Operations",
    "  partly   Handles expiry without scanning the whole table.",
    "           gap: nothing on this",
    "",
    "summary  Strong on the redirect path.",
    "result   2 met · 2 partly · 1 missed of 5 · 9,812 tokens in, 2,410 out · cost unknown",
]


def test_a_review_prints_the_criteria_by_area_and_the_result(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    result = reviewed(monkeypatch, provider, environment)
    assert result.stdout.splitlines() == REVIEW_OUTPUT
    assert result.stderr.splitlines() == ["reviewing with anthropic:claude-x, up to 300 s"]


def test_a_review_is_stored_and_sent_what_the_dry_run_prints(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    dry = invoke(monkeypatch, environment, "--dry-run").stdout
    reviewed(monkeypatch, provider, environment)
    (request,) = sent(provider)
    body = request.json
    assert body["system"] == INSTRUCTIONS
    assert body["system"] in dry
    assert body["messages"][0]["content"] in dry
    listing = invoke(monkeypatch, environment, "--list")
    assert len(listing.stdout.splitlines()) == 2


def test_a_review_never_prints_the_key(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    result = reviewed(monkeypatch, provider, environment)
    assert SECRET not in result.stdout + result.stderr


def test_without_a_slug_the_active_attempt_is_reviewed(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    result = reviewed(monkeypatch, provider, environment)
    assert result.stdout.splitlines()[0].startswith("AI review · url-shortener")


def test_a_reply_that_fails_its_checks_exits_4_and_stores_no_review(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider)
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, complete(["met"]))
    result = invoke(monkeypatch, environment, "url-shortener")
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert "did not follow the review format" in result.stderr
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


def test_a_provider_that_fails_exits_4_without_the_key(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    provider.script(
        Provider.ANTHROPIC,
        Route.COMPLETE,
        Answer(status=401, json={"error": {"message": f"bad key {SECRET}"}}),
    )
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert SECRET not in result.stdout + result.stderr


# consent

QUESTION_START = "AI review of url-shortener sends, from this machine to anthropic, model claude-x:"


def terminal(monkeypatch, answer: bool = True) -> None:
    monkeypatch.setattr(ai_consent_prompt, "stdin_is_terminal", lambda: answer)


def test_the_consent_question_is_asked_at_a_terminal_before_the_request(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider, consent=False)
    terminal(monkeypatch)
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, GOOD)
    result = invoke(monkeypatch, environment, "url-shortener", input="y\n")
    assert result.exit_code == ExitCode.SUCCESS, result.stderr
    assert result.stdout.splitlines() == REVIEW_OUTPUT
    assert result.stderr.splitlines()[0] == QUESTION_START
    assert "  your notes" in result.stderr
    assert result.stderr.index("Send it?") < result.stderr.index("reviewing with")
    assert environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW)


def test_a_no_at_the_consent_question_sends_nothing_and_exits_0(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider, consent=False)
    terminal(monkeypatch)
    result = invoke(monkeypatch, environment, input="n\n")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout.splitlines() == ["not sent"]
    assert "reviewing with" not in result.stderr
    assert sent(provider) == []
    assert environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW) is None
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


def test_without_a_terminal_and_without_a_consent_it_exits_3_naming_the_command(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider, consent=False)
    terminal(monkeypatch, False)
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert (
        "AI review needs your consent to send to anthropic:claude-x: run it once at a terminal, "
        "or cstudy ai consent anthropic:claude-x --purpose review"
    ) in result.stderr
    assert sent(provider) == []


def test_a_recorded_consent_asks_nothing(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    terminal(monkeypatch, False)
    reviewed(monkeypatch, provider, environment)


# refusals


def test_the_cap_refuses_before_the_announcement(tmp_path, monkeypatch, provider):
    settings = AiSettings(enabled=True, model=ANTHROPIC, daily_token_cap=1_000)
    environment = make(tmp_path, provider, settings=settings)
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "the daily token cap is reached" in result.stderr
    assert "reviewing with" not in result.stderr
    assert sent(provider) == []


def test_ai_off_refuses_a_review_and_sends_nothing(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider, settings=AiSettings())
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "AI is off: turn it on with ai.enabled = true" in result.stderr
    assert sent(provider) == []


def test_a_provider_without_a_key_refuses(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider, keys=False)
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "no key for anthropic, which ai.model uses: cstudy ai key anthropic" in result.stderr


def test_notes_that_are_still_the_template_are_refused(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider, notes=None)
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert f"your notes are still the template: write your answer in {NOTES} first" in (
        result.stderr
    )


def test_a_problem_checked_by_tests_is_refused(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    result = invoke(monkeypatch, environment, "two-sum")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "two-sum is checked by tests; AI review is for rubric problems" in result.stderr


def test_an_unknown_problem_exits_3(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    assert invoke(monkeypatch, environment, "no-such-problem").exit_code == ExitCode.USAGE_ERROR


# the dry run


def test_the_dry_run_prints_the_text_the_model_and_the_estimate_and_sends_nothing(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider, consent=False)
    result = invoke(monkeypatch, environment, "--dry-run")
    assert result.exit_code == ExitCode.SUCCESS
    dry = dry_run_review(environment, "url-shortener")
    payload = dry.plan.payload
    assert result.stdout == (
        f"=== instructions review-1 ===\n{payload.instructions}"
        f"=== message ===\n{payload.message}"
        "=== not sent ===\n"
        "model    anthropic:claude-x\n"
        f"estimate about {dry.input_tokens:,} tokens in and up to 16,000 out\n"
    )
    assert ANSWER in result.stdout
    assert sent(provider) == []
    assert environment.ai_store.calls_between(NOW.date(), NOW.date()) == ()
    assert environment.ai_store.consents() == ()
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


def test_the_dry_run_needs_no_key_and_no_consent_with_ai_off_and_no_model(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider, settings=AiSettings(), keys=False, consent=False)
    result = invoke(monkeypatch, environment, "--dry-run")
    assert result.exit_code == ExitCode.SUCCESS
    assert "model    ai.model is not set" in result.stdout
    assert sent(provider) == []


def test_the_dry_run_keeps_the_refusals_about_the_notes(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider, notes=None)
    result = invoke(monkeypatch, environment, "--dry-run")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "your notes are still the template" in result.stderr


# list, show, dismiss


def test_a_problem_without_reviews_says_so(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    result = invoke(monkeypatch, environment, "url-shortener", "--list")
    assert result.stdout.splitlines() == ["no AI reviews of url-shortener yet"]


def test_the_list_has_a_row_per_review_newest_first_with_dismissed_ones_marked(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider)
    reviewed(monkeypatch, provider, environment)
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, complete(["met"] * CRITERIA))
    assert invoke(monkeypatch, environment).exit_code == ExitCode.SUCCESS
    assert invoke(monkeypatch, environment, "--dismiss", "1").exit_code == ExitCode.SUCCESS
    result = invoke(monkeypatch, environment, "url-shortener", "--list")
    assert result.stdout.splitlines() == [
        "REVIEW  ATTEMPT  WHEN        MODEL               RESULT",
        "     2        1  2026-10-24  anthropic:claude-x  5 met · 0 partly · 0 missed of 5",
        "     1        1  2026-10-24  anthropic:claude-x  2 met · 2 partly · 1 missed of 5 · "
        "dismissed",
    ]


def test_show_prints_the_review_as_it_was_printed(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    first = reviewed(monkeypatch, provider, environment)
    shown = invoke(monkeypatch, environment, "--show", "1")
    assert shown.exit_code == ExitCode.SUCCESS
    assert shown.stdout == first.stdout
    assert shown.stderr == ""


def test_show_says_when_the_notes_changed_and_when_the_review_is_dismissed(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider)
    reviewed(monkeypatch, provider, environment)
    environment.workspace.write_text(NOTES, ANSWER + "\nMore.\n")
    invoke(monkeypatch, environment, "--dismiss", "1")
    lines = invoke(monkeypatch, environment, "--show", "1").stdout.splitlines()
    assert lines[2:4] == ["notes changed since this review", "dismissed"]


def test_dismiss_marks_the_review_and_dismissing_it_again_changes_nothing(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider)
    reviewed(monkeypatch, provider, environment)
    first = invoke(monkeypatch, environment, "--dismiss", "1")
    assert first.stdout.splitlines() == ["dismissed AI review 1 of url-shortener"]
    dismissed_at = dismissed(environment)
    again = invoke(monkeypatch, environment, "--dismiss", "1")
    assert again.exit_code == ExitCode.SUCCESS
    assert again.stdout.splitlines() == ["AI review 1 is already dismissed"]
    assert dismissed(environment) == dismissed_at
    assert len(environment.ai_store.reviews_of_problem("url-shortener")) == 1


def test_list_show_and_dismiss_work_with_ai_off_and_send_nothing(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    reviewed(monkeypatch, provider, environment)
    off = replace(environment, config=Config(), credentials=FakeCredentials())
    for arguments in (("--list",), ("--show", "1"), ("--dismiss", "1")):
        assert invoke(monkeypatch, off, *arguments).exit_code == ExitCode.SUCCESS
    assert len(sent(provider)) == 1


@pytest.mark.parametrize("flag", ["--show", "--dismiss"])
def test_an_unknown_review_id_exits_3(tmp_path, monkeypatch, provider, flag):
    environment = make(tmp_path, provider)
    result = invoke(monkeypatch, environment, flag, "9")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "no AI review 9" in result.stderr


# flags that do not go together


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--dry-run", "--list"), "--dry-run and --list cannot be used together"),
        (("--list", "--show", "1"), "--list and --show cannot be used together"),
        (("--show", "1", "--dismiss", "1"), "--show and --dismiss cannot be used together"),
        (("--dry-run", "--json"), "--json does not apply to --dry-run"),
        (("--dismiss", "1", "--json"), "--json does not apply to --dismiss"),
        (("url-shortener", "--show", "1"), "--show takes a review id, not a problem"),
        (("url-shortener", "--dismiss", "1"), "--dismiss takes a review id, not a problem"),
    ],
)
def test_flags_that_do_not_go_together_exit_3_before_anything_happens(
    tmp_path, monkeypatch, provider, arguments, message
):
    environment = make(tmp_path, provider)
    result = invoke(monkeypatch, environment, *arguments)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert message in result.stderr
    assert sent(provider) == []
    assert environment.ai_store.reviews_of_problem("url-shortener") == ()


# --json


def test_json_is_the_document_of_the_new_review(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    document = json.loads(reviewed(monkeypatch, provider, environment, "--json").stdout)
    assert document | {"criteria": None, "created_at": None, "rubric_sha256": None} == {
        "id": "problem/url-shortener",
        "slug": "url-shortener",
        "review_id": 1,
        "attempt_id": 1,
        "format": 1,
        "created_at": None,
        "provider": "anthropic",
        "model": "claude-x",
        "prompt_version": "review-1",
        "rubric_sha256": None,
        "notes_sha256": document["notes_sha256"],
        "notes_changed": False,
        "criteria": None,
        "summary": "Strong on the redirect path.",
        "counts": {"met": 2, "partial": 2, "missing": 1, "total": 5},
        "quotes_dropped": 0,
        "usage": {"input_tokens": 9_812, "output_tokens": 2_410, "cost_usd": None},
        "dismissed_at": None,
    }
    assert [criterion["verdict"] for criterion in document["criteria"]] == [
        "met",
        "partial",
        "missing",
        "met",
        "partial",
    ]
    assert document["criteria"][0]["evidence"] == ["redirects stay fast"]


def test_json_with_show_and_with_list_hold_the_same_review(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    document = json.loads(reviewed(monkeypatch, provider, environment, "--json").stdout)
    shown = json.loads(invoke(monkeypatch, environment, "--show", "1", "--json").stdout)
    listed = json.loads(invoke(monkeypatch, environment, "--list", "--json").stdout)
    assert shown == document
    assert listed == {"id": "problem/url-shortener", "slug": "url-shortener", "reviews": [document]}


def test_json_list_without_a_review_is_empty(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    result = invoke(monkeypatch, environment, "--list", "--json")
    assert json.loads(result.stdout) == {
        "id": "problem/url-shortener",
        "slug": "url-shortener",
        "reviews": [],
    }


def test_json_after_a_no_at_the_consent_question_prints_no_document(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider, consent=False)
    terminal(monkeypatch)
    result = invoke(monkeypatch, environment, "--json", input="n\n")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout == ""
    assert "not sent" in result.stderr


# text from a model


MARKUP_NOTES = "## Design\n\nCache with [bold red]a short TTL[/bold red] in front of the store.\n"


def test_model_text_with_markup_prints_as_it_is(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider, notes=MARKUP_NOTES)
    reply = complete(
        ["partial"] * CRITERIA,
        evidence=("[bold red]a short TTL[/bold red]",),
        gaps="[link=https://example.com]click[/link] [/] [red]gap",
        summary="[bold]Summary[/bold] [/nope]",
    )
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, reply)
    result = invoke(monkeypatch, environment)
    assert result.exit_code == ExitCode.SUCCESS, result.stderr
    assert '"[bold red]a short TTL[/bold red]"' in result.stdout
    assert "gap: [link=https://example.com]click[/link] [/] [red]gap" in result.stdout
    assert "summary  [bold]Summary[/bold] [/nope]" in result.stdout


def stored(environment, **fields) -> int:
    """A review whose text holds what a model's reply never leaves in: it is shown cleaned again."""
    item = ReviewItem(
        1,
        f"Area{ESCAPE}[2J",
        f"Criterion\r{ESCAPE}]0;title\x07 text",
        Verdict.PARTIAL,
        (f"quote{ESCAPE}[31m red\x00 done",),
        f"gap\x08\x08 here\nsecond line{ESCAPE}[0m",
    )
    record = ReviewRecord(
        attempt_id=1,
        created_at=NOW,
        provider=Provider.ANTHROPIC,
        model="claude-x",
        prompt_version="review-1",
        rubric_sha256="0" * 64,
        notes_sha256="1" * 64,
        items=(item,),
        summary=f"summary\r\x07{ESCAPE}[1mbold\nnext",
        quotes_dropped=0,
        input_tokens=None,
        output_tokens=None,
        cost_usd=0.00003,
    )
    return environment.ai_store.add_review(replace(record, **fields))


def test_control_characters_in_a_stored_review_never_reach_the_terminal(
    tmp_path, monkeypatch, provider
):
    environment = make(tmp_path, provider)
    review_id = stored(environment)
    shown = invoke(monkeypatch, environment, "--show", str(review_id))
    listed = invoke(monkeypatch, environment, "--list")
    assert shown.exit_code == ExitCode.SUCCESS
    for text in (shown.stdout, listed.stdout):
        assert ESCAPE not in text
        assert not re.search(r"[\x00-\x09\x0b-\x1f\x7f]", text)
    assert shown.stdout.splitlines()[4:] == [
        "Area[2J",
        "  partly   Criterion",
        "           ]0;title text",
        '           "quote[31m red done"',
        "           gap: gap here",
        "                second line[0m",
        "",
        "summary  summary",
        "         [1mbold",
        "         next",
        "result   0 met · 1 partly · 0 missed of 1 · tokens not reported · $0.00003",
    ]


def test_the_json_document_carries_the_text_unchanged(tmp_path, monkeypatch, provider):
    environment = make(tmp_path, provider)
    review_id = stored(environment)
    document = json.loads(
        invoke(monkeypatch, environment, "--show", str(review_id), "--json").stdout
    )
    assert document["criteria"][0]["gaps"].startswith("gap\x08\x08 here")
    assert document["usage"] == {"input_tokens": None, "output_tokens": None, "cost_usd": 3e-05}
