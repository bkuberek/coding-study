"""The browser engines the Playwright tests of the web UI run on, and what each page logs
(docs/specs/web-ui.md#browser-support).

`webkit` is Playwright's own build of WebKit, the engine of Safari, not the Safari app. Playwright
is in the optional `browser` dependency group: `uv sync --group browser`, then
`uv run --group browser playwright install chromium firefox webkit`. A test on an engine that is
not installed is skipped.
"""

import json
from collections.abc import Callable, Sequence
from typing import Any

import pytest

ENGINES = ("chromium", "firefox", "webkit")
REPORTED_TYPES = ("error", "warning")
VIOLATION_REPORTER = """document.addEventListener("securitypolicyviolation", (event) => {
  console.error(`CSP violation: ${event.violatedDirective} on ${event.target?.nodeName ?? "?"}`);
});"""
"""Names each Content Security Policy violation and its element, which WebKit's own console line
leaves out."""
ENGINE_NOTICES = (
    "Refused to apply a stylesheet because its hash, its nonce, or 'unsafe-inline' does not",
    "CSP violation: style-src-attr on SELECT",
    "CSP violation: style-src-attr on #document",
    "This site appears to use a scroll-linked positioning effect",
)
"""What the engines log of their own, which the page cannot change: WebKit's line for a refused
style, which names no element, so the reporter's line stands for it; a `style-src-attr`
violation that Playwright's WebKit reports for every `<select>`, even one in a static page with
no style and no script, and one on the document when a project's Start dialog, which has no
`<select>`, opens; and a performance hint Firefox logs, now and then, when CodeMirror's
cursor moves while the editor scrolls."""


PLACE_RECORDER = """window.__places = {};
const laidOutTop = (element) => {
  let top = 0;
  for (let found = element; found !== null; found = found.offsetParent) top += found.offsetTop;
  return top;
};
const record = () => {
  for (const selector of SELECTORS) {
    const found = document.querySelector(selector);
    if (found === null) continue;
    const top = laidOutTop(found);
    const places = (window.__places[selector] ??= []);
    if (places.at(-1) !== top) places.push(top);
  }
  requestAnimationFrame(record);
};
requestAnimationFrame(record);"""
"""Notes, frame by frame, each new place in the page's layout of an element of each selector:
its distance from the top of the page, which scrolling, as a click's own, leaves alone."""


def launched(playwright: Any, engine: str) -> Any:
    """The engine's browser, headless; skips the test when Playwright has no such engine."""
    from playwright.sync_api import Error  # pyright: ignore[reportMissingImports]

    try:
        return getattr(playwright, engine).launch()
    except Error as error:
        pytest.skip(f"no {engine} for Playwright: {error.message.splitlines()[0]}")


def save_preferences(page: Any) -> None:
    """Clicks the Settings view's Save and waits until the preferences it staged are stored."""
    page.click(".settings-bar button[type=submit]")
    page.wait_for_selector(".settings-bar p[role=status]:has-text('preferences saved in')")


def watched(
    page: Any, problems: list[str], expected: Callable[[Any], bool] = lambda _: False
) -> Any:
    """`page`, appending to `problems` each error and warning it logs, each CSP violation and
    each uncaught error, but the engines' own notices and the messages `expected` accepts."""
    page.add_init_script(VIOLATION_REPORTER)
    page.on("console", lambda message: _note(problems, message, expected))
    page.on("pageerror", lambda error: problems.append(str(error)))
    return page


def refusing_starts(page: Any, message: str, fix: str) -> None:
    """Makes the server's answer to every start of an attempt `page` sends the `environment`
    refusal with `message` and the CLI's `fix:` hint, as a server on a JDK that cannot run the
    problem's language gives."""
    refusal = {"error": {"code": "environment", "message": message, "fix": fix}}

    def answer(route: Any) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        route.fulfill(status=503, content_type="application/json", body=json.dumps(refusal))

    page.route("**/api/v1/attempts", answer)


def placed(page: Any, selectors: Sequence[str]) -> Any:
    """`page`, noting, frame by frame, each place at which the first element of each of `selectors`
    is laid out, so a test can tell whether what a user is about to click moved after it showed."""
    page.add_init_script(PLACE_RECORDER.replace("SELECTORS", json.dumps(list(selectors))))
    return page


def places(page: Any, selector: str) -> list[int]:
    """The places, in CSS pixels from the top of the page, at which `selector` was laid out so
    far: where it first showed, then each one it moved to."""
    return page.evaluate("selector => window.__places[selector] ?? []", selector)


def _note(problems: list[str], message: Any, expected: Callable[[Any], bool]) -> None:
    if message.type not in REPORTED_TYPES or expected(message):
        return
    if not any(notice in message.text for notice in ENGINE_NOTICES):
        problems.append(f"{message.type}: {message.text}")
