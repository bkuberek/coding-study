"""Fixtures for tests that run beside the app.

`app` asks your app, and `partner` sets the bonus partner's behaviour through the mock server's
control interface, whose address and token `cstudy test` gives your tests. Only the scenarios in
the partner's API.md are there.
"""

import json
import os
from collections.abc import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

TIMEOUT_S = 30


class App:
    def __init__(self, url: str) -> None:
        self._url = url

    def get(self, path: str) -> tuple[int, object]:
        """The status and JSON body the app answers to `GET path`, errors included."""
        return self._send(Request(self._url + path))

    def put(self, path: str, text: str) -> tuple[int, object]:
        """The status and JSON body the app answers to `PUT path` with `text` as its body."""
        request = Request(
            self._url + path,
            data=text.encode(),
            headers={"Content-Type": "text/csv"},
            method="PUT",
        )
        return self._send(request)

    def post(self, path: str, body: object) -> tuple[int, object]:
        """The status and JSON body the app answers to `POST path` with `body` as JSON."""
        request = Request(
            self._url + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._send(request)

    def _send(self, request: Request) -> tuple[int, object]:
        try:
            with urlopen(request, timeout=TIMEOUT_S) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)


class Partner:
    def __init__(self, control_url: str, token: str) -> None:
        self._url = control_url
        self._authorization = {"Authorization": f"Bearer {token}"}

    def set_scenario(self, scenario: str | None) -> None:
        """Makes the partner behave as `scenario` says, or as usual for None."""
        request = Request(
            f"{self._url}/mocks/bonus-partner/scenario",
            data=json.dumps({"scenario": scenario}).encode(),
            headers={**self._authorization, "Content-Type": "application/json"},
            method="PUT",
        )
        try:
            urlopen(request, timeout=TIMEOUT_S).close()
        except HTTPError as error:
            with error:
                reason = error.read().decode()
            raise RuntimeError(f"cannot set {scenario}: {reason}") from error

    def reset(self) -> None:
        """The partner back to no scenario."""
        request = Request(f"{self._url}/reset", headers=self._authorization, method="POST")
        urlopen(request, timeout=TIMEOUT_S).close()


@pytest.fixture
def app() -> App:
    return App(f"http://127.0.0.1:{os.environ['PORT']}")


@pytest.fixture
def partner() -> Iterator[Partner]:
    """The partner, reset to no scenario when the test ends."""
    control = Partner(
        os.environ["CSTUDY_MOCK_CONTROL_URL"], os.environ["CSTUDY_MOCK_CONTROL_TOKEN"]
    )
    yield control
    control.reset()
