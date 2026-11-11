"""The loyalty program's feed service."""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from db import query
from ingest import load_feed, rejects_of
from members import statement, total_points
from reconcile import reconcile

FEED = re.compile(r"/feeds/([A-Za-z0-9._-]+)")
REJECTS = re.compile(r"/feeds/([A-Za-z0-9._-]+)/rejects")
POINTS = re.compile(r"/members/([^/]+)/points")
STATEMENT = re.compile(r"/members/([^/]+)/statement")
MONTH = re.compile(r"[0-9]{4}-(?:0[1-9]|1[0-2])")

NOT_FOUND = {"error": "not_found"}
UNKNOWN_MEMBER = {"error": "unknown_member"}
INVALID_MONTH = {"error": "invalid_month"}


def purchases_of(member: str) -> list[dict[str, Any]]:
    """A member's purchases, oldest first, and by id within a day."""
    rows = query(
        "SELECT id, member, purchased_on, category, amount_cents "
        "FROM purchases WHERE member = :member",
        member=member,
    )
    rows.sort(key=lambda row: (row[2], row[0]))
    return [
        {
            "id": id_,
            "member": member_,
            "date": day.isoformat(),
            "category": category,
            "amount_cents": amount_cents,
        }
        for id_, member_, day, category, amount_cents in rows
    ]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlsplit(self.path)
        arguments = parse_qs(url.query)
        if url.path == "/health":
            self._answer(200, {"status": "ok"})
        elif url.path == "/purchases":
            member = arguments.get("member", [""])[0]
            if member:
                self._answer(200, purchases_of(member))
            else:
                self._answer(400, {"error": "member_required"})
        elif found := REJECTS.fullmatch(url.path):
            self._found(rejects_of(found[1]), {"error": "unknown_feed"})
        elif found := POINTS.fullmatch(url.path):
            self._found(total_points(unquote(found[1])), UNKNOWN_MEMBER)
        elif found := STATEMENT.fullmatch(url.path):
            self._statement(unquote(found[1]), arguments.get("month", [""])[0])
        else:
            self._answer(404, NOT_FOUND)

    def do_PUT(self) -> None:
        found = FEED.fullmatch(urlsplit(self.path).path)
        if found is None:
            self._answer(404, NOT_FOUND)
            return
        result = load_feed(found[1], self._body().decode("utf-8"))
        if result is None:
            self._answer(400, {"error": "invalid_header"})
        else:
            self._answer(200, {"feed": found[1], **vars(result)})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/reconcile":
            self._answer(404, NOT_FOUND)
            return
        try:
            month = json.loads(self._body())["month"]
        except (ValueError, KeyError, TypeError):
            month = None
        if isinstance(month, str) and MONTH.fullmatch(month):
            self._answer(200, reconcile(month))
        else:
            self._answer(400, INVALID_MONTH)

    def _statement(self, member: str, month: str) -> None:
        if not MONTH.fullmatch(month):
            self._answer(400, INVALID_MONTH)
        else:
            self._found(statement(member, month), UNKNOWN_MEMBER)

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", "0")))

    def _found(self, answer: object | None, missing: dict[str, str]) -> None:
        if answer is None:
            self._answer(404, missing)
        else:
            self._answer(200, answer)

    def _answer(self, status: int, body: object) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


def main() -> None:
    port = int(os.environ["PORT"])
    print(f"listening on {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
