"""A workspace with AI on and a rubric attempt in progress, and the provider replies that make a
review of it, for the browser tests of the AI review (docs/specs/web-ui.md#ai-review-in-the-page):
made with the `cstudy` commands a user would run, against no real provider."""

import json
import subprocess
import sys
from pathlib import Path

from tests.ai_workspace import CONFIG, MODEL, SENTINEL_KEY, config_path, plain_workspace
from tests.fake_ai_provider import Answer
from tests.serve_process import served_environment

SLUG = "url-shortener"
NOTES = "notes/system-design/url-shortener.md"
CRITERIA = 28
"""The criteria of `problems/url-shortener/rubric.md`."""
HACK = "<img src=x onerror=window.__pwned=1>"
"""Markup a model's text may hold, which the page must show as text."""
ANSWER = (
    "## Requirements\n\nRedirects stay fast even when creating links is down.\n\n"
    f"Codes are never reused. {HACK}\n"
)
GAP = f"nothing on how fresh click counts must be {HACK}"
SUMMARY = f"Strong on the redirect path. {HACK}"
QUOTES = (
    "Redirects stay fast even when creating links is down.",
    f"Codes are never reused. {HACK}",
)


def _run(workspace: Path, *arguments: str, stdin: str | None = None) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=True,
    )


def review_workspace(directory: Path, *, consented: bool) -> Path:
    """A workspace with `MODEL` set and a key for it, a consent to review with it when
    `consented`, and url-shortener started with its notes written."""
    workspace = plain_workspace(directory)
    config = config_path(workspace)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(CONFIG)
    _run(workspace, "ai", "key", "anthropic", stdin=f"{SENTINEL_KEY}\n")
    if consented:
        _run(workspace, "ai", "consent", MODEL, "--purpose", "review")
    _run(workspace, "start", SLUG, "--no-open")
    notes_path(workspace).write_text(ANSWER)
    return workspace


def notes_path(workspace: Path) -> Path:
    return workspace / NOTES


def review_answer(
    met: int = 18, partial: int = 6, *, summary: str = SUMMARY, delay_s: float = 0.0
) -> Answer:
    """The reply of the fake Anthropic that carries a review of url-shortener: `met` criteria met,
    `partial` partly and the rest missed, the first with quotes the notes hold."""
    verdicts = ["met"] * met + ["partial"] * partial
    verdicts += ["missing"] * (CRITERIA - len(verdicts))
    review = {
        "criteria": [
            {
                "id": f"C{number}",
                "verdict": verdict,
                "evidence": list(QUOTES) if number == 1 else [],
                "gaps": "" if verdict == "met" else GAP,
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
        },
        delay_s=delay_s,
    )
