"""The coworking space's API: what can be booked on a day."""

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from desks import DeskInventory

DESKS = DeskInventory.from_file(Path("data/desks.json"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlsplit(self.path)
        if url.path == "/health":
            self._answer(HTTPStatus.OK, {"status": "ok"})
        elif url.path == "/desks":
            date = parse_qs(url.query).get("date", [""])[0]
            self._answer(
                HTTPStatus.OK, {"date": date, "available": DESKS.available_on(date)}
            )
        else:
            self._answer(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _answer(self, status: HTTPStatus, body: object) -> None:
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
