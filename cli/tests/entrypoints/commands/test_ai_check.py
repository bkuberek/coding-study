"""`cstudy ai check` and `cstudy ai models` (docs/specs/cli.md#cstudy-ai-check and
#cstudy-ai-models) against each provider's recorded replies, served by `tests/fake_ai_provider.py`
behind `CSTUDY_AI_ENDPOINT`."""

import copy
import re
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from coding_study.adapters.ai.http_json import ENDPOINT_VARIABLE, JsonClient
from coding_study.adapters.ai.models import ADAPTERS, ProviderModels
from coding_study.domain.ai import AiTask, ModelRef, Provider, Routing
from coding_study.domain.ai_records import CallOutcome, Consent, ModelCall
from coding_study.domain.config import AiSettings, Config
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import ai_check, ai_consent_prompt
from coding_study.entrypoints.shared import ExitCode
from tests.ai_fixtures import SECRET, recorded
from tests.fake_ai_provider import Answer, FakeAiProvider, Route
from tests.fakes import (
    NOW,
    FakeAiStore,
    FakeClock,
    FakeCredentials,
    make_environment,
    repository_root,
)

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
runner = CliRunner()
MODEL_ID = "m-1"
CHECK_LINE = re.compile(r"^ok · 1\.4 s · [\d,]+ tokens · (\$[\d.]+|cost unknown)$")


class SlowClock(FakeClock):
    """Every reading is 1.4 s after the one before."""

    def now(self) -> datetime:
        self.current += timedelta(seconds=1.4)
        return self.current


STRUCTURED: dict[Provider, tuple[str, Callable[[dict[str, Any]], Any]]] = {
    Provider.ANTHROPIC: ("structured_reply", lambda body: body["content"][-1]),
    Provider.OPENAI: ("structured_reply", lambda body: body["output"][-1]["content"][0]),
    Provider.GOOGLE: ("structured", lambda body: body["candidates"][0]["content"]["parts"][0]),
    Provider.OPENROUTER: ("structured", lambda body: body["choices"][0]["message"]),
}
"""Each provider's recorded structured reply and the part that holds the model's text."""
TEXT_KEY = {
    Provider.ANTHROPIC: "text",
    Provider.OPENAI: "text",
    Provider.GOOGLE: "text",
    Provider.OPENROUTER: "content",
}


def reply_with(provider: Provider, text: str) -> dict[str, Any]:
    """The recorded structured reply of `provider`, with the model saying `text`."""
    name, holder = STRUCTURED[provider]
    body = copy.deepcopy(recorded(provider, name))
    holder(body)[TEXT_KEY[provider]] = text
    return body


@pytest.fixture
def fake() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as provider:
        yield provider


def script_check(
    fake: FakeAiProvider, provider: Provider, *answers: Answer, model_id: str = MODEL_ID
) -> None:
    fake.script(provider, Route.COMPLETE, *answers, model_id=model_id)


def passing(provider: Provider) -> Answer:
    return Answer(json=reply_with(provider, '{"ok": true}'))


def environment_for(tmp_path: Path, fake: FakeAiProvider, settings: AiSettings, keys=None):
    models = ProviderModels(JsonClient({ENDPOINT_VARIABLE: fake.endpoint}, "test"), ADAPTERS)
    return make_environment(
        repository_root(tmp_path, PRACTICE),
        config=Config(ai=settings),
        ai_store=FakeAiStore(),
        credentials=FakeCredentials(keys or {}),
        models=models,
        clock=SlowClock(NOW),
    )


def fixed(provider: Provider, model_id: str = MODEL_ID) -> AiSettings:
    return AiSettings(enabled=True, model=ModelRef(provider, model_id))


def consent(environment, provider: Provider, model_id: str = MODEL_ID) -> None:
    environment.ai_store.grant_consent(Consent(provider, model_id, AiTask.CHECK, NOW))


def check(monkeypatch, environment, input: str | None = None):
    monkeypatch.setattr(ai_check, "load_environment", lambda *_: environment)
    return runner.invoke(cli.app, ["ai", "check"], input=input)


def at_terminal(monkeypatch) -> None:
    monkeypatch.setattr(ai_consent_prompt, "stdin_is_terminal", lambda: True)


def calls_of(environment) -> list[ModelCall]:
    store = environment.ai_store
    assert isinstance(store, FakeAiStore)
    return store.calls


def without_terminal(monkeypatch) -> None:
    monkeypatch.setattr(ai_consent_prompt, "stdin_is_terminal", lambda: False)


# cstudy ai check


@pytest.mark.parametrize("provider", list(Provider))
def test_a_passing_check_prints_one_line_in_each_providers_shape(
    tmp_path, monkeypatch, fake, provider
):
    environment = environment_for(tmp_path, fake, fixed(provider), {provider: SECRET})
    consent(environment, provider)
    script_check(fake, provider, passing(provider))
    result = check(monkeypatch, environment)
    assert result.exit_code == ExitCode.SUCCESS
    (line,) = result.stdout.splitlines()
    model, _, verdict = line.partition("   ")
    assert model == f"{provider}:{MODEL_ID}"
    assert CHECK_LINE.match(verdict.strip())
    assert result.stderr == ""
    assert fake.unanswered == []
    (row,) = calls_of(environment)
    assert (row.purpose, row.provider, row.outcome) == (AiTask.CHECK, provider, CallOutcome.OK)


@pytest.mark.parametrize("provider", list(Provider))
def test_the_key_reaches_the_provider_and_no_output(tmp_path, monkeypatch, fake, provider):
    environment = environment_for(tmp_path, fake, fixed(provider), {provider: SECRET})
    consent(environment, provider)
    script_check(fake, provider, passing(provider))
    result = check(monkeypatch, environment)
    (request,) = fake.requests_to(provider, Route.COMPLETE, MODEL_ID)
    assert SECRET in "".join(request.headers.values())
    assert SECRET not in result.stdout + result.stderr


def test_openrouter_reports_its_cost_and_the_others_do_not(tmp_path, monkeypatch, fake):
    costs: dict[Provider, str] = {}
    for provider in (Provider.OPENROUTER, Provider.ANTHROPIC):
        directory = tmp_path / provider
        environment = environment_for(directory, fake, fixed(provider), {provider: SECRET})
        consent(environment, provider)
        script_check(fake, provider, passing(provider))
        costs[provider] = check(monkeypatch, environment).stdout.strip().split(" · ")[-1]
    assert costs == {Provider.OPENROUTER: "$0.00231", Provider.ANTHROPIC: "cost unknown"}


AUTO = AiSettings(
    enabled=True,
    routing=Routing.AUTO,
    fast=ModelRef(Provider.OPENROUTER, "vendor/fast"),
    strong=ModelRef(Provider.ANTHROPIC, "claude-strong"),
)
AUTO_KEYS = {Provider.OPENROUTER: SECRET + "-or", Provider.ANTHROPIC: SECRET + "-an"}


def auto_environment(tmp_path, fake):
    environment = environment_for(tmp_path, fake, AUTO, AUTO_KEYS)
    consent(environment, Provider.OPENROUTER, "vendor/fast")
    consent(environment, Provider.ANTHROPIC, "claude-strong")
    return environment


def test_auto_routing_shows_each_tier_and_model_in_columns(tmp_path, monkeypatch, fake):
    environment = auto_environment(tmp_path, fake)
    script_check(fake, Provider.OPENROUTER, passing(Provider.OPENROUTER), model_id="")
    script_check(fake, Provider.ANTHROPIC, passing(Provider.ANTHROPIC), model_id="")
    result = check(monkeypatch, environment)
    assert result.exit_code == ExitCode.SUCCESS
    assert [re.sub(r"[\d,]+ tokens", "N tokens", line) for line in result.stdout.splitlines()] == [
        "fast    openrouter:vendor/fast    ok · 1.4 s · N tokens · $0.00231",
        "strong  anthropic:claude-strong   ok · 1.4 s · N tokens · cost unknown",
    ]


def test_a_failing_tier_prints_fail_with_the_error_and_exits_4_after_checking_the_rest(
    tmp_path, monkeypatch, fake
):
    environment = auto_environment(tmp_path, fake)
    script_check(
        fake,
        Provider.OPENROUTER,
        Answer(401, json=recorded(Provider.OPENROUTER, "error_401")),
        model_id="",
    )
    script_check(fake, Provider.ANTHROPIC, passing(Provider.ANTHROPIC), model_id="")
    result = check(monkeypatch, environment)
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    fast, strong = result.stdout.splitlines()
    assert fast == (
        "fast    openrouter:vendor/fast    FAIL openrouter refused the key (401): "
        "set it again with cstudy ai key openrouter"
    )
    assert strong.startswith("strong  anthropic:claude-strong   ok · 1.4 s")
    assert SECRET not in result.stdout + result.stderr
    assert [row.outcome for row in calls_of(environment)] == [
        CallOutcome.FAILED,
        CallOutcome.OK,
    ]


@pytest.mark.parametrize("provider", list(Provider))
def test_a_structured_reply_that_is_not_ok_true_fails_the_check(
    tmp_path, monkeypatch, fake, provider
):
    environment = environment_for(tmp_path, fake, fixed(provider), {provider: SECRET})
    consent(environment, provider)
    script_check(fake, provider, Answer(json=reply_with(provider, '{"ok": false}')))
    result = check(monkeypatch, environment)
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert result.stdout.strip().endswith(
        'FAIL the model\'s reply did not follow the check format: it is not {"ok": true}'
    )


def test_one_model_for_both_tiers_is_checked_once_under_the_fast_tier(tmp_path, monkeypatch, fake):
    same = ModelRef(Provider.ANTHROPIC, MODEL_ID)
    settings = AiSettings(enabled=True, routing=Routing.AUTO, fast=same, strong=same)
    environment = environment_for(tmp_path, fake, settings, {Provider.ANTHROPIC: SECRET})
    consent(environment, Provider.ANTHROPIC)
    script_check(fake, Provider.ANTHROPIC, passing(Provider.ANTHROPIC))
    result = check(monkeypatch, environment)
    (line,) = result.stdout.splitlines()
    assert line.startswith(f"fast  anthropic:{MODEL_ID}   ok · 1.4 s")
    assert len(fake.received) == 1


def test_the_first_check_of_a_model_asks_at_a_terminal_and_a_yes_records_the_consent(
    tmp_path, monkeypatch, fake
):
    provider = Provider.GOOGLE
    environment = environment_for(tmp_path, fake, fixed(provider), {provider: SECRET})
    script_check(fake, provider, passing(provider))
    at_terminal(monkeypatch)
    result = check(monkeypatch, environment, input="y\n")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stderr.splitlines()[0] == (
        f"The check sends, from this machine to google, model {MODEL_ID}:"
    )
    items = [line.split("  ")[1] for line in result.stderr.splitlines()[1:4]]
    assert items == ["instructions check-1", "a fixed test message", "nothing of yours"]
    assert result.stderr.endswith("Send it? [y/N] ")
    assert environment.ai_store.consent(provider, MODEL_ID, AiTask.CHECK) is not None
    assert len(fake.received) == 1


def test_a_no_at_the_terminal_sends_nothing_prints_not_sent_and_exits_0(
    tmp_path, monkeypatch, fake
):
    provider = Provider.OPENAI
    environment = environment_for(tmp_path, fake, fixed(provider), {provider: SECRET})
    at_terminal(monkeypatch)
    result = check(monkeypatch, environment, input="n\n")
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout.strip() == f"openai:{MODEL_ID}   not sent"
    assert fake.received == []
    assert calls_of(environment) == []
    assert environment.ai_store.consents() == ()


def test_without_a_terminal_a_missing_consent_exits_3_and_sends_nothing(
    tmp_path, monkeypatch, fake
):
    provider = Provider.ANTHROPIC
    environment = environment_for(tmp_path, fake, fixed(provider), {provider: SECRET})
    without_terminal(monkeypatch)
    result = check(monkeypatch, environment, input="y\n")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert result.stdout == ""
    assert result.stderr == (
        f"error: The check needs your consent to send to anthropic:{MODEL_ID}: run it once at "
        f"a terminal, or cstudy ai consent anthropic:{MODEL_ID} --purpose check\n"
    )
    assert fake.received == []


@pytest.mark.parametrize(
    ("settings", "keys", "message"),
    [
        (
            AiSettings(),
            {},
            "error: AI is off: turn it on with ai.enabled = true (cstudy config edit) or in "
            "Settings\n",
        ),
        (
            AiSettings(enabled=True),
            {},
            "error: ai.model is not set: choose the model of fixed routing in Settings or with "
            "cstudy config edit\n",
        ),
        (
            fixed(Provider.GOOGLE),
            {},
            "error: no key for google, which ai.model uses: cstudy ai key google, or Settings\n",
        ),
    ],
)
def test_a_check_that_cannot_run_exits_3_before_sending(
    tmp_path, monkeypatch, fake, settings, keys, message
):
    environment = environment_for(tmp_path, fake, settings, keys)
    result = check(monkeypatch, environment)
    assert (result.exit_code, result.stdout, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "",
        message,
    )
    assert fake.received == []


def test_the_cap_refuses_a_check_with_exit_3(tmp_path, monkeypatch, fake):
    provider = Provider.ANTHROPIC
    settings = AiSettings(enabled=True, model=ModelRef(provider, MODEL_ID), daily_token_cap=500)
    environment = environment_for(tmp_path, fake, settings, {provider: SECRET})
    consent(environment, provider)
    result = check(monkeypatch, environment)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "the daily token cap is reached" in result.stderr
    assert fake.received == []


# cstudy ai models


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "home"
    (directory / "work").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(directory))
    monkeypatch.chdir(directory / "work")
    return directory


def run_models(home: Path, fake: FakeAiProvider, *arguments: str, enabled: bool = True):
    config = home / ".config" / "coding-study" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f"[ai]\nenabled = {str(enabled).lower()}\n", encoding="utf-8")
    environ = {
        "CSTUDY_CONFIG": str(config),
        "XDG_CONFIG_HOME": "",
        "CSTUDY_WORKSPACE": "",
        ENDPOINT_VARIABLE: fake.endpoint,
    }
    return runner.invoke(cli.app, ["ai", "models", *arguments], env=environ), environ


def save_key(provider: Provider, environ: dict[str, str]) -> None:
    result = runner.invoke(cli.app, ["ai", "key", provider], input=f"{SECRET}\n", env=environ)
    assert result.exit_code == ExitCode.SUCCESS


LISTINGS = [
    (Provider.ANTHROPIC, ["claude-fast-example", "claude-strong-example"]),
    (Provider.OPENAI, ["gpt-fast-example", "gpt-strong-example", "text-embedding-example"]),
    (Provider.GOOGLE, ["gemini-test-flash", "gemini-test-lite", "gemini-test-pro"]),
    (Provider.OPENROUTER, ["test/model-a", "test/model-b"]),
]


@pytest.mark.parametrize(("provider", "ids"), LISTINGS)
def test_models_prints_the_providers_ids_one_per_line_sorted(home, fake, provider, ids):
    pages = ["models", "models_page_2"] if provider is Provider.GOOGLE else ["models"]
    fake.script(provider, Route.MODELS, *(Answer(json=recorded(provider, p)) for p in pages))
    _, environ = run_models(home, fake, provider)  # no key yet: nothing is requested
    assert fake.received == []
    save_key(provider, environ)
    result, _ = run_models(home, fake, provider)
    assert result.exit_code == ExitCode.SUCCESS
    assert result.stdout.splitlines() == ids
    assert result.stderr == ""
    request = fake.requests_to(provider, Route.MODELS)[0]
    assert SECRET in "".join(request.headers.values())
    assert SECRET not in result.stdout + result.stderr


def test_models_works_in_a_directory_that_is_no_workspace_and_writes_nothing(home, fake):
    fake.script(Provider.OPENAI, Route.MODELS, Answer(json=recorded(Provider.OPENAI, "models")))
    _, environ = run_models(home, fake, Provider.OPENAI)
    save_key(Provider.OPENAI, environ)
    before = sorted(path for path in home.rglob("*"))
    result, _ = run_models(home, fake, Provider.OPENAI)
    assert result.exit_code == ExitCode.SUCCESS
    assert sorted(path for path in home.rglob("*")) == before
    assert not list(home.rglob("progress.db"))


def test_models_without_the_providers_key_exits_3_and_asks_nothing(home, fake):
    result, _ = run_models(home, fake, "google")
    assert (result.exit_code, result.stdout) == (ExitCode.USAGE_ERROR, "")
    assert result.stderr == "error: no key for google: cstudy ai key google, or Settings\n"
    assert fake.received == []


def test_models_with_ai_off_exits_3_and_asks_nothing(home, fake):
    _, environ = run_models(home, fake, "anthropic", enabled=False)
    save_key(Provider.ANTHROPIC, environ)
    result, _ = run_models(home, fake, "anthropic", enabled=False)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert result.stderr == (
        "error: AI is off: turn it on with ai.enabled = true (cstudy config edit) or in Settings\n"
    )
    assert fake.received == []


def test_models_with_an_unknown_provider_exits_3_without_quoting_it(home, fake):
    result, _ = run_models(home, fake, SECRET)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert SECRET not in result.stdout + result.stderr


def test_a_provider_failure_exits_4_without_the_key(home, fake):
    fake.script(
        Provider.ANTHROPIC,
        Route.MODELS,
        Answer(401, json=recorded(Provider.ANTHROPIC, "error_401")),
    )
    _, environ = run_models(home, fake, Provider.ANTHROPIC)
    save_key(Provider.ANTHROPIC, environ)
    result, _ = run_models(home, fake, Provider.ANTHROPIC)
    assert (result.exit_code, result.stdout) == (ExitCode.ENVIRONMENT_ERROR, "")
    assert result.stderr == (
        "error: anthropic refused the key (401): set it again with cstudy ai key anthropic\n"
    )
    assert SECRET not in result.stdout + result.stderr
