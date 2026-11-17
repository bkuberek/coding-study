"""The AI preview for the showcase: the notes of a system design attempt, the review of them that a
model would return, and a loopback server that answers with that review.

No provider is called. `CSTUDY_AI_ENDPOINT` points the served `cstudy` at `DemoProvider`, which
answers Anthropic's messages route with `review_reply()` and refuses every other request, and the
keys the showcase saves are `PLACEHOLDER_KEY`s that no provider would accept. The standard library
only.
"""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

SLUG = "url-shortener"
NOTES_PATH = "notes/system-design/url-shortener.md"
MODEL = "anthropic:claude-sonnet-5-5"
PROVIDERS = ("anthropic", "openai", "openrouter")
"""The providers that get a key; only Anthropic's is ever asked something."""
PLACEHOLDER_KEY = "sk-demo-0000000000000000"
MESSAGES_PATH = "/v1/messages"
CONFIG = f'[ai]\nenabled = true\nrouting = "fixed"\nmodel = "{MODEL}"\n'

NOTES = """# URL Shortener: Notes

## Requirements

- Two paths: create (about 1% of the traffic) and redirect. The redirect is the product: it must
  stay available and fast, p99 under 50 ms in the region, and it stays up even when creating
  links is down.
- Codes are never reused and a destination never changes once created, so a link is write-once.
  That lets redirects be cached everywhere and replicated asynchronously.
- A disabled link must stop redirecting within 1 minute.
- Click counts may lag by a few minutes and may lose a small share of events. I would confirm
  that with the product owner before building the pipeline.
- Out of scope: editing destinations and custom domains.

## Estimates

- 200M new links a month: about 80 creates per second on average, 400 at peak.
- Reads are 100 times the writes: 8,000 redirects per second on average, 40,000 at peak.
- Storage grows by roughly 100 GB a month.
- Codes are 7 characters of base62.

## API

- `POST /links` with the URL and an optional alias returns 201 and the code, or 409 when the
  alias is taken.
- `GET /{code}` answers 302 to the destination, 404 for an unknown code and 410 for a disabled
  link.
- `DELETE /links/{code}` disables a link. `GET /links` lists the caller's links and `GET
  /links/{code}/stats` returns the counts.
- I use 302, not 301: browsers keep a 301 forever, so clicks would never reach us and a disable
  would not take effect.
- Create takes no idempotency key yet; a retry makes a second link.

## Data model

- A key-value store keyed by code, written with a conditional insert (put if absent), which is
  what makes a code unique. Fields: url, owner, created_at, disabled.

## High-level design

- Stateless redirect servers behind a global load balancer in every region, a cache tier in each
  region, and the key-value store replicated asynchronously to every region.
- A redirect appends a click event to a log after it has answered, and a stream job aggregates
  the counts. The redirect never waits for it.
- Abuse: rate limit creates per user.

## Deep dives

- Code generation: random 7-character codes with a conditional insert, and a retry on a
  collision. A counter leaks the volume and makes codes guessable. A pool of pre-generated keys
  adds a service to run. Random wins.
- Hot links: a small in-process cache on each redirect server, in front of the regional cache.
- Disable: the flag is written, then an invalidation goes to every region's caches. Entries also
  carry a 60 s TTL, so the 1-minute goal holds even when a message is lost.
- Click counts: events are delivered at least once and the aggregator deduplicates by event id.

## Failure modes

- Cache tier down: redirect servers read the store directly and shed load above a limit to keep
  the p99.
- Event log down: redirects keep working and the events are dropped.
- Consistency: creates are strongly consistent, through the conditional insert in the code's
  home region. Redirects are eventually consistent, which is safe because a link never changes.

## Observability and cost

- Alert on the redirect p99 and the error rate per region, and watch the cache hit ratio.
- The cost is dominated by the always-on redirect fleet, not by the stored links.
"""

CRITERIA: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("met", ("it stays up even when creating links is down",), ""),
    ("met", ("Codes are never reused and a destination never changes once created",), ""),
    ("met", ("Click counts may lag by a few minutes and may lose a small share of events",), ""),
    ("met", ("Out of scope: editing destinations and custom domains",), ""),
    ("met", ("about 80 creates per second on average, 400 at peak",), ""),
    (
        "partial",
        ("Storage grows by roughly 100 GB a month",),
        "Gives the growth, not the total for 12 billion links or the per-copy size, and does not "
        "conclude that storage is not the hard part.",
    ),
    (
        "partial",
        ("Codes are 7 characters of base62",),
        "States the length but does not justify it from the key space, collisions or guessability.",
    ),
    ("missing", (), "The hot cache is never sized, so there is no check that it fits in memory."),
    ("met", ("returns 201 and the code, or 409 when the alias is taken",), ""),
    ("met", ("I use 302, not 301",), ""),
    ("missing", (), "Names no idempotency key: a retried create makes a second link."),
    (
        "partial",
        ("written with a conditional insert (put if absent)",),
        "Keys the store by code with a conditional insert, but adds no owner index for "
        "`GET /links`.",
    ),
    ("met", ("Stateless redirect servers behind a global load balancer in every region",), ""),
    ("met", ("The redirect never waits for it",), ""),
    (
        "partial",
        ("Abuse: rate limit creates per user",),
        "Limits creates only: no URL scanning at create and no rate limit on 404s.",
    ),
    ("met", ("A counter leaks the volume and makes codes guessable",), ""),
    (
        "partial",
        ("a small in-process cache on each redirect server",),
        "Has the in-process cache, but no single-flight on misses and no negative caching for "
        "unknown codes.",
    ),
    (
        "missing",
        (),
        "Custom aliases are in the API but nothing says how uniqueness holds across regions.",
    ),
    (
        "missing",
        (),
        "Does not say what a region returns for a link created a moment ago elsewhere.",
    ),
    ("met", ("Entries also carry a 60 s TTL",), ""),
    (
        "partial",
        ("the aggregator deduplicates by event id",),
        "Covers at-least-once delivery and deduplication, but not filtering bots and link "
        "previews.",
    ),
    ("met", ("redirect servers read the store directly and shed load",), ""),
    (
        "partial",
        ("redirects keep working and the events are dropped",),
        "Redirects are unaffected, but dropping the events is not a plan: buffer them or spill "
        "them to disk.",
    ),
    (
        "met",
        ("Redirects are eventually consistent, which is safe because a link never changes",),
        "",
    ),
    (
        "missing",
        (),
        "Caching redirects at the CDN, and what it costs in analytics and disable "
        "latency, is not discussed.",
    ),
    (
        "partial",
        ("Alert on the redirect p99 and the error rate per region",),
        "Names p99 and cache hit ratio, but not the 404 rate, analytics lag or disable "
        "propagation time.",
    ),
    ("met", ("dominated by the always-on redirect fleet, not by the stored links",), ""),
    (
        "missing",
        (),
        "Nothing on how editable destinations or custom domains would change the design.",
    ),
)
SUMMARY = (
    "Strong on the redirect path: write-once links, 302 with its analytics and disable trade-off, "
    "random codes with a conditional insert, and a disable that meets the 1-minute goal through "
    "invalidation plus TTL. The main gaps are the cache size, idempotent creates, how custom "
    "aliases stay unique across regions, read-after-create, and what the CDN does to analytics."
)
USAGE = {"input_tokens": 11_430, "output_tokens": 3_108}


def _collapsed(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def review_reply() -> dict[str, Any]:
    """Anthropic's reply to a review request, with the quotes checked against `NOTES` as `cstudy`
    checks them: a quote its notes do not hold is dropped, so one that is not there is a mistake
    here."""
    notes = _collapsed(NOTES)
    criteria: list[dict[str, Any]] = []
    for number, (verdict, quotes, gaps) in enumerate(CRITERIA, start=1):
        for quote in quotes:
            if _collapsed(quote) not in notes:
                raise ValueError(f"C{number}: the notes do not hold the quote {quote!r}")
        criteria.append(
            {"id": f"C{number}", "verdict": verdict, "evidence": list(quotes), "gaps": gaps}
        )
    review = {"criteria": criteria, "summary": SUMMARY}
    return {
        "content": [{"type": "text", "text": json.dumps(review)}],
        "stop_reason": "end_turn",
        "usage": USAGE,
    }


class DemoProvider:
    """A server on the loopback that plays Anthropic for a review and nothing else. `received`
    keeps `(method, path)` of every request it answered, and `refused` those it did not."""

    def __init__(self) -> None:
        self.received: list[tuple[str, str]] = []
        self.refused: list[tuple[str, str]] = []
        self.keys: set[str] = set()
        """The `x-api-key` values it saw."""
        self._body = json.dumps(review_reply()).encode()
        self._server = _server(self)
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        self.endpoint = f"http://127.0.0.1:{self._server.server_address[1]}"

    def __enter__(self) -> "DemoProvider":
        self._thread.start()
        return self

    def __exit__(self, *_exception: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def answer(self, method: str, path: str, key: str | None) -> bytes | None:
        """The body for a request, or None for a refusal."""
        if key:
            self.keys.add(key)
        if method == "POST" and path == MESSAGES_PATH:
            self.received.append((method, path))
            return self._body
        self.refused.append((method, path))
        return None


def _server(provider: DemoProvider) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._serve()

        def do_POST(self) -> None:
            self._serve()

        def _serve(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            path = self.path.partition("?")[0]
            body = provider.answer(self.command, path, self.headers.get("x-api-key"))
            status = 200 if body is not None else 404
            body = body if body is not None else b'{"error": {"message": "not served"}}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
