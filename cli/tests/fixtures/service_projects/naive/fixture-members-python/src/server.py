# pyright: reportMissingImports=false
import json
import os
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pg8000.native

MEMBER = re.compile(r"/members/(\d+)")
PLAN = re.compile(r"/members/(\d+)/plan")
VISITS = re.compile(r"/visits/(\d+)")
NO_MEMBER = {"error": "no such member"}


def connect() -> pg8000.native.Connection:
    url = urlsplit(os.environ["DATABASE_URL"])
    return pg8000.native.Connection(
        url.username or "",
        host=url.hostname,
        port=url.port or 5432,
        database=url.path.lstrip("/"),
        password=url.password,
    )


def query(sql: str, **params: object) -> list[list[object]]:
    database = connect()
    try:
        return database.run(sql, **params)
    finally:
        database.close()


def member(member_id: int) -> dict[str, object] | None:
    rows = query("SELECT id, name FROM members WHERE id = :id", id=member_id)
    return {"id": rows[0][0], "name": rows[0][1]} if rows else None


def plan(member_id: int) -> dict[str, object] | None:
    rows = query("SELECT id, plan FROM members WHERE id = :id", id=member_id)
    return {"id": rows[0][0], "plan": rows[0][1]} if rows else None


def change_plan(member_id: int, chosen: str) -> dict[str, object] | None:
    sql = "UPDATE members SET plan = :plan WHERE id = :id RETURNING id, plan"
    rows = query(sql, id=member_id, plan=chosen)
    return {"id": rows[0][0], "plan": rows[0][1]} if rows else None


def visit(member_id: int) -> int:
    """INCR over the Redis protocol, which the standard library can speak."""
    url = urlsplit(os.environ["REDIS_URL"])
    key = f"visits:{member_id}".encode()
    with socket.create_connection((url.hostname, url.port or 6379), 5) as cache:
        cache.sendall(b"*2\r\n$4\r\nINCR\r\n$%d\r\n%s\r\n" % (len(key), key))
        return int(cache.recv(64).strip().lstrip(b":"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            self._answer(200, {"status": "ok"})
        elif found := PLAN.fullmatch(path):
            self._found(plan(int(found[1])))
        elif found := MEMBER.fullmatch(path):
            self._found(member(int(found[1])))
        else:
            self._answer(404, {"error": "not found"})

    def do_POST(self) -> None:
        found = VISITS.fullmatch(urlsplit(self.path).path)
        if found:
            self._answer(200, {"member": int(found[1]), "visits": visit(int(found[1]))})
        else:
            self._answer(404, {"error": "not found"})

    def do_PUT(self) -> None:
        found = PLAN.fullmatch(urlsplit(self.path).path)
        if found is None:
            self._answer(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        chosen = json.loads(self.rfile.read(length))["plan"]
        self._found(change_plan(int(found[1]), chosen))

    def _found(self, answer: dict[str, object] | None) -> None:
        if answer is None:
            self._answer(404, NO_MEMBER)
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
