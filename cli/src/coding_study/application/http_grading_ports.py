"""What the HTTP grader asks of a stack and of the network
(docs/specs/service-projects.md#http-grading).

The grader starts nothing and waits for nothing to come up: it is handed a stack that is ready.
Startup runs on the sandbox's clock, so no time limit or hang guard of a case counts it, and that
holds for each restart here too: a restart returns once the app answers its health path again.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import ExchangeFailed, HttpResponse, MockLog
from coding_study.domain.http_origins import split_url


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
    app_origin: str | None = None
    """The app's own origin inside the stack, `http://app:<port>`, which a case's absolute URL
    names and which a path alone shares its cookies with. None reaches the app at `app_url`
    alone."""
    origins: Mapping[str, str] = field(default_factory=dict[str, str])
    """The contract P10's services plug into (docs/specs/service-projects.md#reaching-an-origin):
    for each other origin a case may name, by its name inside the stack, `http://idp:8080`, where
    the grader reaches it on this machine, `http://127.0.0.1:<port>`, through the forwarder."""
    reach: Mapping[str, str] = field(default_factory=dict[str, str])
    """`http://127.0.0.1:<port>` by each `<name>:<port>` in `project.grader_reach`, the origin the
    app's network knows it by, such as `idp:8080`. A client dials the URL and sends that origin as
    `Host`, which the forwarder passes on untouched (docs/specs/service-projects.md#grader-reach).
    The app's own origin, `app:<app.port>`, is `app_url`."""

    def address_of(self, origin: str | None) -> str | None:
        """Where the grader dials a request for `origin`; None is the app. None back when the
        stack publishes nothing for it."""
        if origin is None or origin in (self.app_origin, _origin_of(self.app_url)):
            return self.app_url
        return self.origins.get(origin)


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

    def app_output(self, since_s: float) -> str:
        """What the app printed, standard output and error together, since `since_s`, in seconds
        since the epoch. Raises RunnerStartError when it cannot be read: a stack that stopped
        working is no verdict on your code."""
        ...


class AppClient(Protocol):
    """Sends a case's requests to the app, or to another origin the stack publishes, as a browser
    would: with the cookies of the request's jar, and following redirects when it asks."""

    def send(self, request: HttpRequest, limit_ms: int) -> HttpResponse | ExchangeFailed:
        """The whole exchange, connecting through the last byte of the body, within `limit_ms`,
        redirects followed included."""
        ...

    def clear_cookies(self) -> None:
        """Empties every jar: each case starts with no cookies."""
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


def _origin_of(url: str) -> str | None:
    split = split_url(url)
    return split[0] if split is not None else None
