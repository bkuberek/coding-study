"""The Settings view's AI section in a real browser (docs/specs/web-ui.md#settings-view), in each
engine of `tests/browsers.py`, against a real `cstudy serve` whose child `cstudy` reaches the fake
provider of `tests/fake_ai_provider.py`: AI off, with Check and Load models waiting; a model, a key
and the switch staged and saved in one Save, the key never in the page again; Load models offering
the ids a provider lists as text; Check asking its consent in the dialog, which sends nothing on
Cancel or Escape and sends on Send; the consent listed and revoked; a key refused and a key
removed; the routing choosing which model keys show.

No test calls a real provider. Playwright and its engines are set up as `tests/browsers.py` says;
without them the test is skipped.
"""

import copy
import stat
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.ai import Provider
from tests.ai_fixtures import recorded
from tests.ai_workspace import MODEL, SENTINEL_KEY, config_path, credentials_path, plain_workspace
from tests.browsers import launched, watched
from tests.fake_ai_provider import Answer, FakeAiProvider, Route
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
WIDE = {"width": 1440, "height": 900}
READY = "#ai-key-anthropic-state:has-text('no key'), #ai-key-anthropic-state:has-text('key set')"
SECTION = "section.settings-ai"
BAR = ".settings-bar"
SAVE = f"{BAR} button[type=submit]"
RESET = f"{BAR} button:has-text('Reset')"
COUNT = f"{BAR} .settings-count"
STATUS = f"{BAR} p[role=status]"
ENABLED = "#config-ai-enabled"
FIXED = "#config-ai-routing-fixed"
AUTO = "#config-ai-routing-auto"
MODEL_FIELD = "#config-ai-model"
FAST_FIELD = "#config-ai-fast"
KEY = "#ai-key-anthropic"
KEY_STATE = "#ai-key-anthropic-state"
REMOVE = "button[aria-label$='the key for anthropic']"
LOAD = "button[aria-label='Load models of anthropic']"
CHECK = "#ai-models .ai-actions button"
REASON = "#ai-actions-reason"
JOB_STATE = "#ai-models section.job .job-state"
JOB_LOG = "#ai-models section.job .job-log"
MODEL_IDS = "#ai-model-ids option"
SHEET = "dialog.sheet[open]"
CONSENTS = ".ai-consents li"
REVOKED = ".ai-revoked"
TODAY = ".ai-today"
CONFLICT = "status of 409"
REFUSED = "status of 422"
HACK = "<img/src=x/onerror=window.__pwned=1>"
CHECK_REPLY = "structured_reply"


def _structured(text: str) -> dict[str, Any]:
    body = copy.deepcopy(recorded(Provider.ANTHROPIC, CHECK_REPLY))
    body["content"][-1]["text"] = text
    return body


def _models() -> dict[str, Any]:
    body = copy.deepcopy(recorded(Provider.ANTHROPIC, "models"))
    body["data"].append({"type": "model", "id": HACK, "display_name": "Hack"})
    return body


@dataclass
class Seen:
    """What the section said and did, step by step."""

    legends: list[str] = field(default_factory=list[str])
    heading: str = ""
    docs_link: str = ""
    preview_marks: int = 0
    off_check_disabled: bool = False
    off_reason: str = ""
    off_load_disabled: bool = False
    key_attributes: dict[str, str] = field(default_factory=dict[str, str])
    staged_count: str = ""
    staged_key_state: str = ""
    staged_reason: str = ""
    staged_on_reason: str = ""
    staged_check_disabled: bool = False
    saved_says: str = ""
    key_after_save: str = "unset"
    page_after_save: str = ""
    values_after_save: list[str] = field(default_factory=list[str])
    key_state_after_save: str = ""
    count_after_save_visible: bool = True
    check_enabled_after_save: bool = False
    config_after_save: dict[str, Any] = field(default_factory=dict[str, Any])
    credentials_mode: int = 0
    models_state: str = ""
    models_log: str = ""
    model_ids: list[str] = field(default_factory=list[str])
    pwned: bool = False
    images: int = 0
    models_requests: int = 0
    consent_title: str = ""
    consent_text: str = ""
    consent_buttons: list[str] = field(default_factory=list[str])
    consent_focus: str = ""
    sent_after_cancel: int = -1
    focus_after_cancel: str = ""
    sent_after_escape: int = -1
    check_state: str = ""
    check_log: str = ""
    sent_after_send: int = 0
    consent_listed: list[str] = field(default_factory=list[str])
    today_line: str = ""
    asked_again: bool = True
    revoked_says: str = ""
    consents_after_revoke: list[str] = field(default_factory=list[str])
    consents_in_status: list[Any] = field(default_factory=list[Any])
    remove_label: str = ""
    removal_state: str = ""
    removal_count: str = ""
    reset_state: str = ""
    reset_count_visible: bool = True
    refused_says: str = ""
    refused_count: str = ""
    removed_says: str = ""
    credentials_after_removal: bool = True
    key_state_after_removal: str = ""
    load_disabled_after_removal: bool = False
    auto_fast_visible: bool = False
    auto_model_visible: bool = True
    fixed_fast_visible: bool = True
    fixed_model_visible: bool = False
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return plain_workspace(tmp_path_factory.mktemp(f"settings-ai-{engine}"))


@pytest.fixture(scope="module")
def fake() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as provider:
        provider.script(Provider.ANTHROPIC, Route.MODELS, Answer(json=_models()))
        provider.script(
            Provider.ANTHROPIC, Route.COMPLETE, Answer(json=_structured('{"ok": true}'))
        )
        yield provider


@pytest.fixture(scope="module")
def server(workspace: Path, fake: FakeAiProvider) -> Iterator[RunningServer]:
    with running_server(workspace, variables={"CSTUDY_AI_ENDPOINT": fake.endpoint}) as running:
        yield running


def _expected(message: Any) -> bool:
    return CONFLICT in message.text or REFUSED in message.text


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, workspace: Path, fake: FakeAiProvider) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport=WIDE), found.logged, _expected)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("location.hash = '#/settings'")
        page.wait_for_selector(READY)
        page.wait_for_selector(ENABLED)
        _off(page, found)
        _stage_and_save(page, workspace, found)
        _load_models(page, fake, found)
        _check(page, fake, found)
        _revoke(page, found)
        _refused_key(page, found)
        _remove_key(page, workspace, found)
        _routing(page, found)
        browser.close()
    return found


def _text(page: Any, selector: str) -> str:
    return " ".join(page.locator(selector).inner_text().split())


def _status_says(page: Any, text: str) -> str:
    page.wait_for_selector(f"{STATUS}:has-text('{text}')")
    return page.locator(STATUS).inner_text()


def _off(page: Any, seen: Seen) -> None:
    seen.legends = page.locator(f"{SECTION} fieldset.ai-group > legend").all_text_contents()
    seen.heading = page.locator(f"{SECTION} h2").inner_text()
    seen.docs_link = page.get_attribute(f"{SECTION} a[href^='#/docs']", "href") or ""
    seen.preview_marks = page.locator(f"{SECTION} .preview-mark").count()
    page.wait_for_selector(f"{REASON}:has-text('AI is off')")
    seen.off_check_disabled = page.is_disabled(CHECK)
    seen.off_reason = _text(page, REASON)
    seen.off_load_disabled = page.is_disabled(LOAD)
    seen.key_attributes = page.eval_on_selector(
        KEY,
        "e => ({type: e.type, autocomplete: e.autocomplete, spellcheck: String(e.spellcheck),"
        " value: e.value})",
    )


def _stage_and_save(page: Any, workspace: Path, seen: Seen) -> None:
    page.check(ENABLED)
    page.fill(MODEL_FIELD, MODEL)
    page.fill(KEY, SENTINEL_KEY)
    seen.staged_count = _text(page, COUNT)
    seen.staged_key_state = _text(page, KEY_STATE)
    seen.staged_reason = _text(page, REASON)
    seen.staged_check_disabled = page.is_disabled(CHECK)
    page.click(SAVE)
    seen.saved_says = _status_says(page, "credentials.toml saved")
    page.wait_for_selector(f"{KEY_STATE}:text-is('key set')")
    seen.key_after_save = page.input_value(KEY)
    seen.page_after_save = page.content()
    seen.values_after_save = page.eval_on_selector_all(
        "input", "inputs => inputs.map(input => input.value)"
    )
    seen.key_state_after_save = _text(page, KEY_STATE)
    seen.count_after_save_visible = page.is_visible(COUNT)
    page.wait_for_selector(f"{CHECK}:not([disabled])")
    seen.check_enabled_after_save = True
    seen.config_after_save = tomllib.loads(config_path(workspace).read_text())
    seen.credentials_mode = stat.S_IMODE(credentials_path(workspace).stat().st_mode)


def _load_models(page: Any, fake: FakeAiProvider, seen: Seen) -> None:
    page.click(LOAD)
    page.wait_for_selector(f"{JOB_STATE}:has-text('exit 0')")
    seen.models_state = _text(page, JOB_STATE)
    seen.models_log = page.locator(JOB_LOG).inner_text()
    seen.model_ids = page.eval_on_selector_all(MODEL_IDS, "options => options.map(o => o.value)")
    seen.pwned = bool(page.evaluate("window.__pwned === 1"))
    seen.images = page.locator(f"{SECTION} img").count()
    seen.models_requests = len(fake.requests_to(Provider.ANTHROPIC, Route.MODELS))


def _open_check(page: Any) -> None:
    page.click(CHECK)
    page.wait_for_selector(SHEET)


def _check(page: Any, fake: FakeAiProvider, seen: Seen) -> None:
    def sends() -> int:
        return len(fake.requests_to(Provider.ANTHROPIC, Route.COMPLETE))

    _open_check(page)
    seen.consent_title = page.locator(f"{SHEET} h2").inner_text()
    seen.consent_text = _text(page, f"{SHEET} .sheet-body")
    seen.consent_buttons = page.locator(f"{SHEET} .sheet-actions button").all_inner_texts()
    seen.consent_focus = page.evaluate("document.activeElement?.textContent")
    page.click(f"{SHEET} button:has-text('Cancel')")
    page.wait_for_selector(SHEET, state="detached")
    seen.sent_after_cancel = sends()
    seen.focus_after_cancel = page.evaluate("document.activeElement?.textContent")
    _open_check(page)
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    seen.sent_after_escape = sends()
    _open_check(page)
    page.click(f"{SHEET} button:has-text('Send')")
    page.wait_for_selector(SHEET, state="detached")
    page.wait_for_selector(f"{JOB_STATE}:has-text('exit 0')")
    seen.check_state = _text(page, JOB_STATE)
    seen.check_log = page.locator(JOB_LOG).inner_text()
    seen.sent_after_send = sends()
    page.wait_for_selector(f"{CONSENTS}:has-text('· check ·')")
    seen.consent_listed = page.locator(CONSENTS).all_inner_texts()
    page.wait_for_selector(f"{TODAY}:has-text('1 request')")
    seen.today_line = _text(page, TODAY)


def _status_document(page: Any) -> dict[str, Any]:
    return page.evaluate("fetch('/api/v1/ai/status').then(response => response.json())")


def _revoke(page: Any, seen: Seen) -> None:
    page.click(f"{CONSENTS} button:has-text('Revoke')")
    page.wait_for_selector(f"{REVOKED}:has-text('revoked')")
    seen.revoked_says = _text(page, REVOKED)
    page.wait_for_selector(f"{CONSENTS}:has-text('no consent recorded')")
    seen.consents_after_revoke = page.locator(CONSENTS).all_inner_texts()
    seen.consents_in_status = _status_document(page)["consents"]


def _refused_key(page: Any, seen: Seen) -> None:
    """A key with a space is refused by the server, which never quotes it, and stays staged."""
    page.fill(KEY, "a key with spaces")
    seen.staged_on_reason = _text(page, REASON)
    page.click(SAVE)
    seen.refused_says = _status_says(page, "credentials.toml not saved")
    seen.refused_count = _text(page, COUNT)
    page.click(RESET)
    page.wait_for_selector(COUNT, state="hidden")


def _remove_key(page: Any, workspace: Path, seen: Seen) -> None:
    page.click(REMOVE)
    seen.remove_label = page.locator(REMOVE).inner_text()
    seen.removal_state = _text(page, KEY_STATE)
    seen.removal_count = _text(page, COUNT)
    page.click(RESET)
    seen.reset_state = _text(page, KEY_STATE)
    seen.reset_count_visible = page.is_visible(COUNT)
    page.click(REMOVE)
    page.click(SAVE)
    seen.removed_says = _status_says(page, "credentials.toml saved")
    page.wait_for_selector(f"{KEY_STATE}:text-is('no key')")
    seen.credentials_after_removal = credentials_path(workspace).exists()
    seen.key_state_after_removal = _text(page, KEY_STATE)
    seen.load_disabled_after_removal = page.is_disabled(LOAD)


def _routing(page: Any, seen: Seen) -> None:
    page.check(AUTO)
    seen.auto_fast_visible = page.is_visible(FAST_FIELD)
    seen.auto_model_visible = page.is_visible(MODEL_FIELD)
    page.click(RESET)
    page.wait_for_selector(f"{FIXED}:checked")
    seen.fixed_fast_visible = page.is_visible(FAST_FIELD)
    seen.fixed_model_visible = page.is_visible(MODEL_FIELD)


def test_the_section_shows_with_ai_off_in_four_groups_and_names_its_stores(seen):
    assert seen.heading == "AI (preview)"
    assert seen.legends == ["Turn on", "Keys", "Models", "This workspace"]
    assert seen.docs_link == "#/docs/ai"
    assert seen.preview_marks >= 5


def test_check_and_load_models_wait_while_ai_is_off_with_the_reason_tied_to_them(seen):
    assert (seen.off_check_disabled, seen.off_load_disabled) == (True, True)
    assert seen.off_reason.startswith("AI is off")


def test_a_key_field_is_a_password_field_that_never_autocompletes_and_starts_empty(seen):
    assert seen.key_attributes == {
        "type": "password",
        "autocomplete": "off",
        "spellcheck": "false",
        "value": "",
    }


def test_a_switch_a_model_and_a_key_stage_together_and_wait_for_save(seen):
    assert seen.staged_count == "3 changes"
    assert seen.staged_key_state == "no key · new key staged"
    assert seen.staged_check_disabled
    assert seen.staged_reason.startswith("AI is off")
    assert seen.staged_on_reason.startswith("Save your AI changes first")


def test_save_writes_the_config_then_the_credentials_and_names_each_store(seen):
    assert seen.saved_says.splitlines()[0].startswith("config.toml saved: ")
    assert "credentials.toml saved: a key for anthropic" in seen.saved_says
    assert seen.config_after_save["ai"] == {"enabled": True, "model": MODEL}
    assert seen.check_enabled_after_save


def test_the_key_file_is_private_and_the_key_is_never_shown_again(seen):
    assert seen.credentials_mode == 0o600
    assert seen.key_after_save == ""
    assert SENTINEL_KEY not in seen.page_after_save
    assert SENTINEL_KEY not in "".join(seen.values_after_save)
    assert seen.key_state_after_save == "key set"
    assert not seen.count_after_save_visible


def test_load_models_runs_the_job_and_offers_each_id_as_text_never_markup(seen):
    assert seen.models_state.endswith("exit 0")
    assert seen.models_requests == 1
    assert seen.model_ids == [
        f"anthropic:{HACK}",
        "anthropic:claude-fast-example",
        "anthropic:claude-strong-example",
    ]
    assert HACK in seen.models_log
    assert (seen.pwned, seen.images) == (False, 0)


def test_the_consent_dialog_names_the_model_what_it_sends_and_what_it_costs(seen):
    assert seen.consent_title == f"Send to {MODEL}?"
    for text in (
        "cstudy ai consent",
        "The check sends, from this machine:",
        "a fixed test message",
        "nothing of yours",
        "tokens in, up to",
        "today 0 of",
        "Your anthropic account's terms apply to what it receives.",
        "cstudy asks once for this model and the check.",
    ):
        assert text in seen.consent_text
    assert seen.consent_buttons == ["Cancel", "Send"]


def test_cancel_holds_the_focus_and_cancel_and_escape_send_nothing(seen):
    assert seen.consent_focus == "Cancel"
    assert seen.sent_after_cancel == 0
    assert seen.focus_after_cancel == "Check"
    assert seen.sent_after_escape == 0


def test_send_runs_the_check_records_the_consent_and_counts_the_request(seen):
    assert seen.check_state.endswith("exit 0")
    assert "ok" in seen.check_log
    assert seen.sent_after_send == 1
    assert len(seen.consent_listed) == 1
    assert seen.consent_listed[0].startswith(f"{MODEL} · check · since ")
    assert seen.today_line.startswith("today: ")
    assert "1 request" in seen.today_line


def test_revoke_acts_at_once_and_says_cstudy_asks_again(seen):
    assert seen.revoked_says == "revoked: cstudy asks again next time"
    assert seen.consents_after_revoke == [
        "no consent recorded: cstudy asks before the first request that sends"
    ]
    assert seen.consents_in_status == []


def test_a_refused_key_says_which_store_never_quotes_it_and_stays_staged(seen):
    assert seen.refused_says.startswith("credentials.toml not saved: anthropic: ")
    assert "a key with spaces" not in seen.refused_says
    assert SENTINEL_KEY not in seen.refused_says
    assert seen.refused_count == "1 change"


def test_remove_stages_a_removal_that_reset_undoes_and_save_writes(seen):
    assert seen.remove_label == "Keep"
    assert seen.removal_state == "key set · removal staged"
    assert seen.removal_count == "1 change"
    assert (seen.reset_state, seen.reset_count_visible) == ("key set", False)
    assert seen.removed_says == "credentials.toml saved: removed the key for anthropic"
    assert not seen.credentials_after_removal
    assert seen.key_state_after_removal == "no key"
    assert seen.load_disabled_after_removal


def test_the_routing_chooses_the_model_keys_that_show(seen):
    assert (seen.auto_fast_visible, seen.auto_model_visible) == (True, False)
    assert (seen.fixed_fast_visible, seen.fixed_model_visible) == (False, True)


def test_the_page_logged_no_error_and_no_csp_violation(seen):
    assert seen.logged == []
