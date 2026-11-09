"""Fixtures for tests that run beside the app.

`app` asks your app, and `vendors` sets a vendor's behaviour through the mock servers'
control interface, whose address and token `cstudy test` gives your tests. Only the
scenarios in a vendor's API.md are there.
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
        try:
            with urlopen(self._url + path, timeout=TIMEOUT_S) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)


class Vendors:
    def __init__(self, control_url: str, token: str) -> None:
        self._url = control_url
        self._authorization = {"Authorization": f"Bearer {token}"}

    def set_scenario(self, vendor: str, scenario: str | None) -> None:
        """Makes `vendor` behave as `scenario` says, or as usual for None."""
        request = Request(
            f"{self._url}/mocks/{vendor}/scenario",
            data=json.dumps({"scenario": scenario}).encode(),
            headers={**self._authorization, "Content-Type": "application/json"},
            method="PUT",
        )
        try:
            urlopen(request, timeout=TIMEOUT_S).close()
        except HTTPError as error:
            with error:
                reason = error.read().decode()
            raise RuntimeError(
                f"cannot set {scenario} on {vendor}: {reason}"
            ) from error

    def reset(self) -> None:
        """Every vendor back to no scenario."""
        request = Request(
            f"{self._url}/reset", headers=self._authorization, method="POST"
        )
        urlopen(request, timeout=TIMEOUT_S).close()


@pytest.fixture
def app() -> App:
    return App(f"http://127.0.0.1:{os.environ['PORT']}")


@pytest.fixture
def vendors() -> Iterator[Vendors]:
    """The vendors, reset to no scenario when the test ends."""
    control = Vendors(
        os.environ["CSTUDY_MOCK_CONTROL_URL"], os.environ["CSTUDY_MOCK_CONTROL_TOKEN"]
    )
    yield control
    control.reset()
