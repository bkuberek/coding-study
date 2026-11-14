"""The loyalty program's feed service."""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from db import query

FEED = re.compile(r"/feeds/([A-Za-z0-9._-]+)")


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
        if url.path == "/health":
            self._answer(200, {"status": "ok"})
        elif url.path == "/purchases":
            member = parse_qs(url.query).get("member", [""])[0]
            if member:
                self._answer(200, purchases_of(member))
            else:
                self._answer(400, {"error": "member_required"})
        else:
            self._answer(404, {"error": "not_found"})

    def do_PUT(self) -> None:
        found = FEED.fullmatch(urlsplit(self.path).path)
        if found is None:
            self._answer(404, {"error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        feed_text = self.rfile.read(length).decode("utf-8")
        self._answer(501, {"error": "not_implemented", "feed": found[1], "bytes": len(feed_text)})

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
