# pyright: reportMissingImports=false
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pg8000.native

MEMBER = re.compile(r"/members/(\d+)")


def connect() -> pg8000.native.Connection:
    url = urlsplit(os.environ["DATABASE_URL"])
    return pg8000.native.Connection(
        url.username or "",
        host=url.hostname,
        port=url.port or 5432,
        database=url.path.lstrip("/"),
        password=url.password,
    )


def member(member_id: int) -> dict[str, object] | None:
    database = connect()
    try:
        rows = database.run("SELECT id, name FROM members WHERE id = :id", id=member_id)
    finally:
        database.close()
    return {"id": rows[0][0], "name": rows[0][1]} if rows else None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        found = MEMBER.fullmatch(path)
        if path == "/health":
            self._answer(200, {"status": "ok"})
        elif found:
            answer = member(int(found[1]))
            if answer is None:
                self._answer(404, {"error": "no such member"})
            else:
                self._answer(200, answer)
        else:
            self._answer(404, {"error": "not found"})

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
