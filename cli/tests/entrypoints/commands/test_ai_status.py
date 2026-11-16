"""`cstudy ai status`, `usage` and `consent` (docs/specs/cli.md#cstudy-ai), and the consent
question at a terminal (docs/specs/ai.md#consent), over fakes and a fake clock."""

import io
import json
from datetime import timedelta
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from coding_study.adapters.toml_credentials import open_credentials
from coding_study.application.ai_send import ConsentQuestion, SentItem
from coding_study.domain.ai import AiTask, ModelRef, Provider, Routing, Tier
from coding_study.domain.ai_records import CallOutcome, Consent, ModelCall
from coding_study.domain.ai_routing import Target
from coding_study.domain.config import AiSettings, Config
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import ai, ai_consent_prompt
from coding_study.entrypoints.commands.ai_consent_prompt import TerminalAsker
from coding_study.entrypoints.shared import ExitCode, add_command
from tests.fakes import (
    NOW,
    FakeAiStore,
    FakeClock,
    FakeCredentials,
    make_environment,
    repository_root,
)

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
OPENROUTER = ModelRef(Provider.OPENROUTER, "vendor/model")
TODAY = NOW.date()
AUTO = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER, strong=ANTHROPIC)
SECRET = "sk-sentinel-0123456789"
runner = CliRunner()


def make(tmp_path: Path, ai_settings: AiSettings, keys=None, issue=None):
    return make_environment(
        repository_root(tmp_path, PRACTICE),
        config=Config(ai=ai_settings),
        ai_store=FakeAiStore(),
        credentials=FakeCredentials(keys or {}, issue),
    )


def invoke(monkeypatch, environment, *arguments: str):
    monkeypatch.setattr(ai, "load_environment", lambda *_: environment)
    return runner.invoke(cli.app, ["ai", *arguments])


def call(
    day=TODAY,
    provider=Provider.ANTHROPIC,
    model="claude-x",
    purpose=AiTask.REVIEW,
    outcome=CallOutcome.OK,
    input_tokens=1_000,
    output_tokens=500,
    cost=None,
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
        input_tokens,
        output_tokens,
        input_tokens + output_tokens,
        cost,
    )


def grant(environment, model: ModelRef, purpose: AiTask) -> None:
    environment.ai_store.grant_consent(Consent(model.provider, model.model_id, purpose, NOW))


# cstudy ai status


def test_ai_status_with_ai_off_says_nothing_is_sent(tmp_path, monkeypatch):
    result = invoke(monkeypatch, make(tmp_path, AiSettings()), "status")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout.splitlines() == [
        "ai        off: nothing is sent; turn it on with ai.enabled = true (cstudy config edit) "
        "or in Settings",
        "review    AI is off",
        "check     AI is off",
        "keys      none · in /fake/config/credentials.toml",
        "consents  none",
        "today     0 of 500,000 tokens · 0 requests",
    ]


def test_ai_status_with_auto_routing_lists_the_models_keys_consents_and_today(
    tmp_path, monkeypatch
):
    environment = make(
        tmp_path, AUTO, {Provider.ANTHROPIC: SECRET, Provider.OPENROUTER: SECRET + "2"}
    )
    grant(environment, ANTHROPIC, AiTask.REVIEW)
    grant(environment, OPENROUTER, AiTask.CHECK)
    environment.ai_store.record_call(call(cost=None))
    environment.ai_store.record_call(call(cost=None))
    environment.ai_store.record_call(
        call(provider=Provider.OPENROUTER, purpose=AiTask.CHECK, cost=0.00003)
    )
    result = invoke(monkeypatch, environment, "status")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout.splitlines() == [
        "ai        on · routing auto · fast openrouter:vendor/model · strong anthropic:claude-x",
        "review    ready · strong anthropic:claude-x",
        "check     ready · fast openrouter:vendor/model, strong anthropic:claude-x",
        "keys      anthropic, openrouter · in /fake/config/credentials.toml",
        "consents  anthropic:claude-x review (2026-10-24) · "
        "openrouter:vendor/model check (2026-10-24)",
        "today     4,500 of 500,000 tokens · 3 requests · $0.00003 known, "
        "2 requests without a reported cost",
    ]
    assert SECRET not in result.stdout + result.stderr


def test_ai_status_with_fixed_routing_names_the_one_model(tmp_path, monkeypatch):
    settings = AiSettings(enabled=True, model=ANTHROPIC)
    result = invoke(monkeypatch, make(tmp_path, settings, {Provider.ANTHROPIC: SECRET}), "status")
    assert result.stdout.splitlines()[:3] == [
        "ai        on · routing fixed · anthropic:claude-x",
        "review    ready · anthropic:claude-x",
        "check     ready · anthropic:claude-x",
    ]


def test_ai_status_says_why_a_task_cannot_run(tmp_path, monkeypatch):
    settings = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER)
    result = invoke(monkeypatch, make(tmp_path, settings, {Provider.OPENROUTER: SECRET}), "status")
    assert result.stdout.splitlines()[:3] == [
        "ai        on · routing auto · fast openrouter:vendor/model · strong not set",
        "review    ai.strong is not set",
        "check     ai.strong is not set",
    ]


def test_ai_status_says_which_provider_has_no_key(tmp_path, monkeypatch):
    result = invoke(monkeypatch, make(tmp_path, AUTO, {Provider.ANTHROPIC: SECRET}), "status")
    assert result.stdout.splitlines()[1:3] == [
        "review    ready · strong anthropic:claude-x",
        "check     no key for openrouter",
    ]


def test_ai_status_with_a_credentials_file_that_does_not_load_shows_its_problem(
    tmp_path, monkeypatch
):
    problem = '/fake/config/credentials.toml: unknown provider "antropic"'
    result = invoke(monkeypatch, make(tmp_path, AUTO, issue=problem), "status")
    assert result.exit_code == ExitCode.SUCCESS
    lines = result.stdout.splitlines()
    assert lines[3] == f"keys      {problem}"
    assert lines[1:3] == [f"review    {problem}", f"check     {problem}"]


def test_ai_status_over_a_real_credentials_file_that_does_not_load(
    tmp_path, tmp_path_factory, monkeypatch
):
    config = tmp_path_factory.mktemp("config")
    (config / "credentials.toml").write_text(f'[antropic]\napi_key = "{SECRET}"\n')
    root = repository_root(tmp_path, PRACTICE)
    credentials = open_credentials({"CSTUDY_CONFIG": str(config / "config.toml")}, tmp_path, root)
    environment = make_environment(
        root, config=Config(ai=AUTO), ai_store=FakeAiStore(), credentials=credentials
    )
    result = invoke(monkeypatch, environment, "status")
    assert result.exit_code == ExitCode.SUCCESS
    assert "unknown provider" in result.stdout
    assert SECRET not in result.stdout + result.stderr


def test_ai_status_json_is_the_document(tmp_path, monkeypatch):
    environment = make(tmp_path, AUTO, {Provider.ANTHROPIC: SECRET})
    grant(environment, ANTHROPIC, AiTask.REVIEW)
    environment.ai_store.record_call(call(cost=0.5))
    result = invoke(monkeypatch, environment, "status", "--json")
    assert result.exit_code == ExitCode.SUCCESS
    document = json.loads(result.stdout)
    assert document["models"] == {
        "model": None,
        "fast": "openrouter:vendor/model",
        "strong": "anthropic:claude-x",
    }
    assert document["tasks"][0] == {
        "task": "review",
        "models": [{"tier": "strong", "model": "anthropic:claude-x"}],
        "ready": True,
        "reason": None,
    }
    assert document["credentials"]["keys"] == {
        "anthropic": True,
        "google": False,
        "openai": False,
        "openrouter": False,
    }
    assert document["consents"] == [
        {
            "provider": "anthropic",
            "model": "claude-x",
            "purpose": "review",
            "granted_at": NOW.isoformat(),
        }
    ]
    assert document["today"] == {
        "day": "2026-10-24",
        "tokens": 1_500,
        "cap": 500_000,
        "requests": 1,
        "cost_usd": 0.5,
        "requests_without_cost": 0,
    }
    assert SECRET not in result.stdout


def test_ai_status_json_with_ai_off_has_no_tier_under_fixed_routing_and_a_reason(
    tmp_path, monkeypatch
):
    settings = AiSettings(model=ANTHROPIC)
    document = json.loads(invoke(monkeypatch, make(tmp_path, settings), "status", "--json").stdout)
    assert document["enabled"] is False
    assert document["tasks"][0] == {
        "task": "review",
        "models": [{"tier": None, "model": "anthropic:claude-x"}],
        "ready": False,
        "reason": document["tasks"][0]["reason"],
    }
    assert document["tasks"][0]["reason"].startswith("AI is off")


# cstudy ai usage


def test_ai_usage_without_a_request_says_so(tmp_path, monkeypatch):
    result = invoke(monkeypatch, make(tmp_path, AiSettings()), "usage")
    assert (result.exit_code, result.stdout) == (
        ExitCode.SUCCESS,
        "no AI requests in the last 7 days\n",
    )


def test_ai_usage_prints_a_row_per_day_provider_model_and_purpose(tmp_path, monkeypatch):
    environment = make(tmp_path, AUTO)
    yesterday = TODAY - timedelta(days=1)
    environment.ai_store.record_call(call(day=yesterday, input_tokens=9_000, output_tokens=4_000))
    environment.ai_store.record_call(
        call(day=yesterday, input_tokens=812, output_tokens=820, outcome=CallOutcome.FAILED)
    )
    environment.ai_store.record_call(
        call(
            provider=Provider.OPENROUTER,
            model="m",
            purpose=AiTask.CHECK,
            input_tokens=40,
            output_tokens=12,
            cost=0.00003,
        )
    )
    result = invoke(monkeypatch, environment, "usage", "--days", "2")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout.splitlines() == [
        "DAY         PROVIDER    MODEL     PURPOSE  REQUESTS  INPUT  OUTPUT  COST",
        "2026-10-23  anthropic   claude-x  review          2  9,812   4,820  -",
        "2026-10-24  openrouter  m         check           1     40      12  $0.00003",
        "total       3 requests, 1 failed · 14,684 tokens counted · "
        "$0.00003 known, 2 requests without a reported cost",
    ]


def test_ai_usage_leaves_out_the_days_before_the_window(tmp_path, monkeypatch):
    environment = make(tmp_path, AUTO)
    environment.ai_store.record_call(call(day=TODAY - timedelta(days=3)))
    result = invoke(monkeypatch, environment, "usage", "--days", "2")
    assert result.stdout == "no AI requests in the last 2 days\n"


def test_ai_usage_with_one_request_and_no_known_cost_says_cost_unknown(tmp_path, monkeypatch):
    environment = make(tmp_path, AUTO)
    environment.ai_store.record_call(call())
    result = invoke(monkeypatch, environment, "usage")
    assert result.stdout.splitlines()[-1] == (
        "total       1 request, 0 failed · 1,500 tokens counted · cost unknown"
    )


def test_ai_usage_json_is_the_document(tmp_path, monkeypatch):
    environment = make(tmp_path, AUTO)
    environment.ai_store.record_call(call(cost=0.25))
    document = json.loads(invoke(monkeypatch, environment, "usage", "--days", "3", "--json").stdout)
    assert (document["days"], document["from"], document["to"]) == (3, "2026-10-22", "2026-10-24")
    assert document["rows"] == [
        {
            "day": "2026-10-24",
            "provider": "anthropic",
            "model": "claude-x",
            "purpose": "review",
            "requests": 1,
            "failed": 0,
            "input_tokens": 1_000,
            "output_tokens": 500,
            "counted_tokens": 1_500,
            "cost_usd": 0.25,
            "requests_without_cost": 0,
        }
    ]
    assert document["total"]["requests"] == 1


def test_ai_usage_json_without_a_request_has_no_rows_and_no_cost(tmp_path, monkeypatch):
    document = json.loads(invoke(monkeypatch, make(tmp_path, AUTO), "usage", "--json").stdout)
    assert document["rows"] == []
    assert document["total"]["cost_usd"] is None


@pytest.mark.parametrize("days", ["0", "367", "-1", "abc"])
def test_ai_usage_rejects_days_outside_1_to_366(tmp_path, monkeypatch, days):
    result = invoke(monkeypatch, make(tmp_path, AUTO), "usage", "--days", days)
    assert result.exit_code == ExitCode.USAGE_ERROR


# cstudy ai consent


def test_ai_consent_records_it_and_works_with_ai_off_and_no_key(tmp_path, monkeypatch):
    environment = make(tmp_path, AiSettings())
    result = invoke(
        monkeypatch, environment, "consent", "anthropic:claude-x", "--purpose", "review"
    )
    assert (result.exit_code, result.stdout) == (
        ExitCode.SUCCESS,
        "consent recorded: anthropic:claude-x for AI review\n",
    )
    assert environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW) is not None


def test_ai_consent_for_the_check_names_the_check(tmp_path, monkeypatch):
    result = invoke(
        monkeypatch, make(tmp_path, AiSettings()), "consent", "openai:gpt-x", "--purpose", "check"
    )
    assert result.stdout == "consent recorded: openai:gpt-x for the check\n"


def test_ai_consent_keeps_the_model_id_with_colons_and_slashes(tmp_path, monkeypatch):
    environment = make(tmp_path, AiSettings())
    invoke(monkeypatch, environment, "consent", "openrouter:vendor/m:free", "--purpose", "check")
    assert environment.ai_store.consent(Provider.OPENROUTER, "vendor/m:free", AiTask.CHECK)


def test_ai_consent_twice_keeps_the_first_day(tmp_path, monkeypatch):
    environment = make(tmp_path, AiSettings())
    arguments = ("consent", "anthropic:claude-x", "--purpose", "review")
    invoke(monkeypatch, environment, *arguments)
    assert isinstance(environment.clock, FakeClock)
    environment.clock.advance(timedelta(days=2))
    invoke(monkeypatch, environment, *arguments)
    stored = environment.ai_store.consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW)
    assert stored is not None
    assert stored.granted_at == NOW


def test_ai_consent_revoke_removes_it(tmp_path, monkeypatch):
    environment = make(tmp_path, AiSettings())
    grant(environment, ANTHROPIC, AiTask.REVIEW)
    result = invoke(
        monkeypatch, environment, "consent", "anthropic:claude-x", "--purpose", "review", "--revoke"
    )
    assert (result.exit_code, result.stdout) == (
        ExitCode.SUCCESS,
        "consent revoked: anthropic:claude-x for AI review\n",
    )
    assert environment.ai_store.consents() == ()


def test_ai_consent_revoke_without_a_consent_says_so_and_keeps_the_others(tmp_path, monkeypatch):
    environment = make(tmp_path, AiSettings())
    grant(environment, ANTHROPIC, AiTask.CHECK)
    result = invoke(
        monkeypatch, environment, "consent", "anthropic:claude-x", "--purpose", "review", "--revoke"
    )
    assert (result.exit_code, result.stdout) == (
        ExitCode.SUCCESS,
        "no consent to revoke for anthropic:claude-x and AI review\n",
    )
    assert len(environment.ai_store.consents()) == 1


@pytest.mark.parametrize("model", ["claude-x", "anthropic:", "mistral:large", "anthropic:a b"])
def test_ai_consent_for_something_that_is_not_a_model_exits_3(tmp_path, monkeypatch, model):
    result = invoke(
        monkeypatch, make(tmp_path, AiSettings()), "consent", model, "--purpose", "check"
    )
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert result.stderr.startswith("error: ")


def test_ai_consent_for_an_unknown_purpose_exits_3(tmp_path, monkeypatch):
    result = invoke(
        monkeypatch, make(tmp_path, AiSettings()), "consent", "openai:gpt-x", "--purpose", "chat"
    )
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "unknown purpose" in result.stderr


def test_ai_consent_requires_a_purpose(tmp_path, monkeypatch):
    result = invoke(monkeypatch, make(tmp_path, AiSettings()), "consent", "openai:gpt-x")
    assert result.exit_code == ExitCode.USAGE_ERROR


# The consent question at a terminal

QUESTION = ConsentQuestion(
    AiTask.REVIEW,
    Target(Tier.STRONG, ANTHROPIC),
    (
        SentItem("instructions review-1", 2_150),
        SentItem("prompt.md", 1_640),
        SentItem("rubric.md, 28 criteria", 3_280),
        SentItem("your notes", 4_300, "notes/system-design/url-shortener.md"),
    ),
    2_800,
    16_000,
    12_400,
    500_000,
)
CHECK_QUESTION = ConsentQuestion(
    AiTask.CHECK,
    Target(None, OPENROUTER),
    (
        SentItem("instructions check-1"),
        SentItem("a fixed test message"),
        SentItem("nothing of yours"),
    ),
    300,
    1_000,
    0,
    500_000,
)


def at_terminal(monkeypatch, typed: str) -> None:
    monkeypatch.setattr(ai_consent_prompt, "stdin_is_terminal", lambda: True)
    monkeypatch.setattr("sys.stdin", io.StringIO(typed))


def test_the_question_lists_what_is_sent_and_asks_yes_or_no(monkeypatch, capsys):
    at_terminal(monkeypatch, "y\n")
    assert TerminalAsker("url-shortener").ask(QUESTION) is True
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "AI review of url-shortener sends, from this machine to anthropic, model claude-x:\n"
        "  instructions review-1         2.1 KB\n"
        "  prompt.md                     1.6 KB\n"
        "  rubric.md, 28 criteria        3.2 KB\n"
        "  your notes                    4.2 KB  notes/system-design/url-shortener.md\n"
        "about 2,800 tokens in and up to 16,000 out · today 12,400 of 500,000 tokens\n"
        "Your anthropic account's terms apply to what it receives. "
        "cstudy asks once for this model and AI review.\n"
        "Send it? [y/N] "
    )


def test_the_check_is_asked_the_same_way_without_a_subject(monkeypatch, capsys):
    at_terminal(monkeypatch, "yes\n")
    assert TerminalAsker().ask(CHECK_QUESTION) is True
    lines = capsys.readouterr().err.splitlines()
    assert lines[0] == "The check sends, from this machine to openrouter, model vendor/model:"
    assert lines[1:4] == [
        "  instructions check-1",
        "  a fixed test message",
        "  nothing of yours",
    ]
    assert lines[-2].endswith("cstudy asks once for this model and the check.")
    assert lines[-1] == "Send it? [y/N] "


@pytest.mark.parametrize("typed", ["Y\n", "YES\n", " y \n"])
def test_yes_in_any_case_sends(monkeypatch, typed):
    at_terminal(monkeypatch, typed)
    assert TerminalAsker().ask(QUESTION) is True


@pytest.mark.parametrize("typed", ["n\n", "no\n", "\n", "maybe\n", "yy\n"])
def test_no_and_enter_and_anything_else_do_not_send(monkeypatch, typed):
    at_terminal(monkeypatch, typed)
    assert TerminalAsker().ask(QUESTION) is False


def test_end_of_input_does_not_send(monkeypatch):
    at_terminal(monkeypatch, "")
    assert TerminalAsker().ask(QUESTION) is False


def test_without_a_terminal_nothing_is_asked_and_the_command_exits_3(monkeypatch):
    monkeypatch.setattr(ai_consent_prompt, "stdin_is_terminal", lambda: False)
    app = typer.Typer()

    def ask() -> None:
        TerminalAsker().ask(QUESTION)

    add_command(app, ask, "ask")
    result = runner.invoke(app, [], input="y\n")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert result.stdout == ""
    assert result.stderr == (
        "error: AI review needs your consent to send to anthropic:claude-x: run it once at a "
        "terminal, or cstudy ai consent anthropic:claude-x --purpose review\n"
    )
