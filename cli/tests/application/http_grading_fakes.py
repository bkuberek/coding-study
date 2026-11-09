"""A ready stack and its clients, in memory, for the HTTP grader's flow. Each step is written to one
journal, so a test can say in what order they came."""

from dataclasses import dataclass, field
from typing import Any

from coding_study.application.http_grading_ports import (
    AppExit,
    StackClients,
    StackEndpoints,
    StackStepError,
)
from coding_study.domain.cases import Case, Expected
from coding_study.domain.http_case import HttpCaseInput, HttpExpected, HttpRequest
from coding_study.domain.http_grading import ExchangeFailed, HttpResponse, MockLog

type Sent = HttpResponse | ExchangeFailed

APP_URL = "http://127.0.0.1:8000"
CONTROL_URL = "http://127.0.0.1:9000"
CONTROL_TOKEN = "fake-token"
APP_ORIGIN = "http://app:8000"
ROOM_VENDOR = "room-vendor"
ANSWERED = HttpResponse(200, {}, b"")


@dataclass
class FakeStack:
    journal: list[str]
    mocks: tuple[str, ...] = (ROOM_VENDOR,)
    exit: AppExit | None = None
    restart_problem: str | None = None
    exit_waits: list[int] = field(default_factory=list[int])
    output_since: list[float] = field(default_factory=list[float])
    origins: dict[str, str] = field(default_factory=dict[str, str])
    output: str = ""
    """What the app printed, for each case that asks."""

    @property
    def endpoints(self) -> StackEndpoints:
        return StackEndpoints(
            APP_URL, CONTROL_URL, CONTROL_TOKEN, self.mocks, APP_ORIGIN, self.origins
        )

    def restart_app(self) -> None:
        self.journal.append("restart app")
        self._maybe_fail()

    def restart_app_with_fresh_data(self) -> None:
        self.journal.append("restart app with fresh data")
        self._maybe_fail()

    def app_exit(self, within_ms: int) -> AppExit | None:
        self.exit_waits.append(within_ms)
        return self.exit

    def app_output(self, since_s: float) -> str:
        self.journal.append("read app output")
        self.output_since.append(since_s)
        return self.output

    def _maybe_fail(self) -> None:
        if self.restart_problem is not None:
            raise StackStepError(self.restart_problem, "output of the reset")


@dataclass
class FakeApp:
    journal: list[str]
    answers: dict[str, Sent] = field(default_factory=dict[str, Sent])
    """By target, or by origin and target for a request to a named origin."""
    limits: list[int] = field(default_factory=list[int])
    sent: list[HttpRequest] = field(default_factory=list[HttpRequest])
    cookie_clears: int = 0

    def send(self, request: HttpRequest, limit_ms: int) -> Sent:
        where = f"{request.origin or ''}{request.target}"
        self.journal.append(f"send {request.method} {where}")
        self.limits.append(limit_ms)
        self.sent.append(request)
        return self.answers.get(where, ANSWERED)

    def clear_cookies(self) -> None:
        self.cookie_clears += 1


@dataclass
class FakeMockControl:
    journal: list[str]
    unknown_scenarios: frozenset[str] = frozenset()
    logs: dict[str, MockLog] = field(default_factory=dict[str, MockLog])

    def reset(self) -> None:
        self.journal.append("mocks reset")

    def set_scenario(self, mock: str, scenario: str) -> bool:
        self.journal.append(f"scenario {mock}={scenario}")
        return scenario not in self.unknown_scenarios

    def log(self, mock: str) -> MockLog:
        self.journal.append(f"log {mock}")
        return self.logs.get(mock, MockLog())


@dataclass
class Rig:
    """One fake stack with its clients, all on one journal."""

    journal: list[str] = field(default_factory=list[str])

    def __post_init__(self) -> None:
        self.stack = FakeStack(self.journal)
        self.app = FakeApp(self.journal)
        self.control = FakeMockControl(self.journal)

    def open_clients(self, endpoints: StackEndpoints) -> StackClients:
        return StackClients(self.app, self.control)


def http_case(case_id: str = "h1", *, path: str = "/a", **fields: Any) -> Case:
    """A case of level 1 unless `level` says otherwise; `visible`, `hang_guard_ms` and `note` go to
    the case, everything else to its HTTP input."""
    expected: HttpExpected = fields.pop("expected", HttpExpected(200))
    case_fields = {
        name: fields.pop(name) for name in ("visible", "hang_guard_ms", "note") if name in fields
    }
    level: int = fields.pop("level", 1)
    http = HttpCaseInput(
        {"method": "GET", "path": path},
        request=HttpRequest("GET", path),
        expected=expected,
        **fields,
    )
    return Case(case_id, http, Expected({"status": expected.status}), level=level, **case_fields)
