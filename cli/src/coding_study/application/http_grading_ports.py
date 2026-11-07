"""What the HTTP grader asks of a stack and of the network
(docs/specs/service-projects.md#http-grading).

The grader starts nothing and waits for nothing to come up: it is handed a stack that is ready.
Startup runs on the sandbox's clock, so no time limit or hang guard of a case counts it, and that
holds for each restart here too: a restart returns once the app answers its health path again.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import ExchangeFailed, HttpResponse, MockLog


@dataclass(frozen=True, slots=True)
class StackEndpoints:
    """Where a ready stack answers on your machine, through the forwarder's published ports."""

    app_url: str
    """`http://127.0.0.1:<port>`."""
    control_url: str | None
    """`http://127.0.0.1:<port>` of the mock control interface; None without mock servers."""
    control_token: str
    mocks: tuple[str, ...]
    """The names of the problem's mock servers."""


@dataclass(frozen=True, slots=True)
class AppExit:
    """How the app ended."""

    exit_code: int
    stderr_tail: str = ""


class StackStepError(Exception):
    """A restart, or the `reset` command inside one, did not leave the app ready."""

    def __init__(self, message: str, output_tail: str = "") -> None:
        super().__init__(message)
        self.output_tail = output_tail


class GradedStack(Protocol):
    """A ready stack, as the HTTP grader sees it. P3's sandbox implements this over its
    `ReadyStack`, which holds the published ports."""

    @property
    def endpoints(self) -> StackEndpoints: ...

    def restart_app(self) -> None:
        """Stops the app and starts it again, for a case that hung it. Returns once its health
        path answers; raises StackStepError when it does not."""
        ...

    def restart_app_with_fresh_data(self) -> None:
        """For a case with `fresh: true`: stops the app, runs the declared `commands.reset` with
        `CSTUDY_RESET_PHASE=apply` if there is one, and starts the app again. Returns once its
        health path answers; raises StackStepError when `reset` fails or the app does not."""
        ...

    def app_exit(self, within_ms: int) -> AppExit | None:
        """How the app ended, or None if it is still running after waiting up to `within_ms`: a
        container's exit shows a moment after its connections drop."""
        ...


class AppClient(Protocol):
    """Sends a case's requests to the app."""

    def send(self, request: HttpRequest, limit_ms: int) -> HttpResponse | ExchangeFailed:
        """The whole exchange, connecting through the last byte of the body, within `limit_ms`."""
        ...


class MockControl(Protocol):
    """The mock control interface (docs/specs/service-projects.md#control-interface). A failure to
    reach it raises RunnerStartError: a stack that stopped working is no verdict on your code."""

    def reset(self) -> None:
        """Clears the logs and counters, and sets every mock server to no scenario."""
        ...

    def set_scenario(self, mock: str, scenario: str) -> bool:
        """False when the mock server has no scenario of that name."""
        ...

    def log(self, mock: str) -> MockLog: ...


@dataclass(frozen=True, slots=True)
class StackClients:
    app: AppClient
    mocks: MockControl


type OpenStackClients = Callable[[StackEndpoints], StackClients]
"""`open_stack_clients` in `adapters/http_grader/clients.py`, or a fake in a test."""
