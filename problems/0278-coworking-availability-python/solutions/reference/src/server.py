"""The coworking space's API: what can be booked on a day."""

import json
import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import date
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import parse_qs, urlsplit

from availability import room_availability
from dates import parse_day
from desks import DeskInventory
from vendors import RoomSource
from vendors.annex_vendor import AnnexVendor
from vendors.room_vendor import RoomVendor

log = logging.getLogger(__name__)


class Reply(NamedTuple):
    status: HTTPStatus
    body: object


class Refused(Exception):
    """A request this API will not answer for its date, with the reply that says why."""

    def __init__(self, status: HTTPStatus, error: str) -> None:
        super().__init__(error)
        self.reply = Reply(status, {"error": error})


class CoworkingApi:
    """Every answer the API gives, from a request's method and target; no HTTP."""

    def __init__(self, desks: DeskInventory, vendors: Sequence[RoomSource]) -> None:
        self._desks = desks
        self._vendors = vendors
        self._routes: dict[str, Callable[[str], Reply]] = {
            "/health": lambda _date: Reply(HTTPStatus.OK, {"status": "ok"}),
            "/desks": self._desks_on,
            "/availability": self._availability_on,
        }

    def answer(self, method: str, target: str) -> Reply:
        url = urlsplit(target)
        route = self._routes.get(url.path)
        if route is None:
            return Reply(HTTPStatus.NOT_FOUND, {"error": "not found"})
        if method != "GET":
            return Reply(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})
        text = parse_qs(url.query).get("date", [""])[0]
        try:
            return route(text)
        except Refused as refused:
            return refused.reply

    def _desks_on(self, text: str) -> Reply:
        _, available = self._on_sale(text)
        return Reply(HTTPStatus.OK, {"date": text, "available": available})

    def _availability_on(self, text: str) -> Reply:
        day, available = self._on_sale(text)
        rooms = room_availability(day, self._vendors)
        body = {"date": text, "desks": {"available": available}, "rooms": asdict(rooms)}
        return Reply(HTTPStatus.OK, body)

    def _on_sale(self, text: str) -> tuple[date, int]:
        """The day `text` names, and its desks left.

        Raises Refused for a day this API does not answer, before a vendor hears of it.
        """
        if not text:
            raise Refused(HTTPStatus.BAD_REQUEST, "date is required")
        day = parse_day(text)
        if day is None:
            raise Refused(
                HTTPStatus.BAD_REQUEST, "date must be a real day, as YYYY-MM-DD"
            )
        available = self._desks.available_on(text)
        if available is None:
            raise Refused(HTTPStatus.NOT_FOUND, "no desks on sale for that date")
        return day, available


class Handler(BaseHTTPRequestHandler):
    """HTTP in and out; every method goes to the API, which refuses all but GET."""

    def __init__(self, *args: Any, api: CoworkingApi, **kwargs: Any) -> None:
        self._api = api
        super().__init__(*args, **kwargs)

    def _reply(self) -> None:
        try:
            status, body = self._api.answer(self.command, self.path)
        except Exception:
            log.exception("no answer to %s %s", self.command, self.path)
            status, body = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal error"}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _reply


def main() -> None:
    api = CoworkingApi(
        DeskInventory.from_file(Path("data/desks.json")),
        [
            RoomVendor(os.environ["ROOM_VENDOR_URL"]),
            AnnexVendor(os.environ["ANNEX_VENDOR_URL"]),
        ],
    )
    port = int(os.environ["PORT"])
    print(f"listening on {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, api=api)).serve_forever()


if __name__ == "__main__":
    main()
