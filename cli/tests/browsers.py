"""The browser engines the Playwright tests of the web UI run on, and what each page logs
(docs/specs/web-ui.md#browser-support).

`webkit` is Playwright's own build of WebKit, the engine of Safari, not the Safari app. Playwright
is in the optional `browser` dependency group: `uv sync --group browser`, then
`uv run --group browser playwright install chromium firefox webkit`. A test on an engine that is
not installed is skipped.
"""

from collections.abc import Callable
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
    "This site appears to use a scroll-linked positioning effect",
)
"""What the engines log of their own, which the page cannot change: WebKit's line for a refused
style, which names no element, so the reporter's line stands for it; a `style-src-attr`
violation that Playwright's WebKit reports for every `<select>`, even one in a static page with
no style and no script; and a performance hint Firefox logs, now and then, when CodeMirror's
cursor moves while the editor scrolls."""


def launched(playwright: Any, engine: str) -> Any:
    """The engine's browser, headless; skips the test when Playwright has no such engine."""
    from playwright.sync_api import Error

    try:
        return getattr(playwright, engine).launch()
    except Error as error:
        pytest.skip(f"no {engine} for Playwright: {error.message.splitlines()[0]}")


def watched(
    page: Any, problems: list[str], expected: Callable[[Any], bool] = lambda _: False
) -> Any:
    """`page`, appending to `problems` each error and warning it logs, each CSP violation and
    each uncaught error, but the engines' own notices and the messages `expected` accepts."""
    page.add_init_script(VIOLATION_REPORTER)
    page.on("console", lambda message: _note(problems, message, expected))
    page.on("pageerror", lambda error: problems.append(str(error)))
    return page


def _note(problems: list[str], message: Any, expected: Callable[[Any], bool]) -> None:
    if message.type not in REPORTED_TYPES or expected(message):
        return
    if not any(notice in message.text for notice in ENGINE_NOTICES):
        problems.append(f"{message.type}: {message.text}")
