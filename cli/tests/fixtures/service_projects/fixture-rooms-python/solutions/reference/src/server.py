import json
import os
import re
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

STOCK = Path(os.environ["CSTUDY_DATA_DIR"]) / "stock.json"
VENDOR = os.environ["ROOM_VENDOR_URL"]
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
DEGRADED = {"rooms": [], "degraded": True}
VENDOR_LIMIT_S = 1.0


def vendor_call() -> bytes:
    with urllib.request.urlopen(f"{VENDOR}/v1/rooms", timeout=VENDOR_LIMIT_S) as answer:
        return answer.read()


def rooms() -> object:
    try:
        try:
            body = vendor_call()
        except urllib.error.HTTPError as error:
            if error.code != 429:
                return DEGRADED
            time.sleep(int(error.headers.get("Retry-After", "1")))
            body = vendor_call()
        return {"rooms": json.loads(body)["rooms"], "degraded": False}
    except (OSError, ValueError):
        return DEGRADED


def available() -> int:
    return json.loads(STOCK.read_text())["available"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlsplit(self.path)
        if url.path == "/health":
            self._answer(200, {"status": "ok"})
        elif url.path == "/desks":
            date = parse_qs(url.query).get("date", [""])[0]
            if DATE.fullmatch(date):
                self._answer(200, {"date": date, "available": available()})
            else:
                self._answer(400, {"error": "date is required"})
        elif url.path == "/rooms":
            self._answer(200, rooms())
        else:
            self._answer(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlsplit(self.path).path == "/desks/book":
            left = available() - 1
            STOCK.write_text(json.dumps({"available": left}))
            self._answer(201, {"available": left})
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
