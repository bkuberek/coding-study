"""A stand-in app, the real mock server and the real clients on loopback, with no container: what a
graded run does once its stack is ready."""

import json
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.http_grader.case_document import http_case_input
from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.application.run_events import CaseGraded
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected
from coding_study.domain.config import Config
from coding_study.domain.judging import CaseVerdict, Judgement
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from coding_study.domain.runs import Raised, TimedOut
from coding_study.entrypoints.commands._events import event_value
from coding_study.entrypoints.commands.report_text import case_details
from tests.adapters.http_grader.standin_app import (
    ROOM_VENDOR,
    AppAnswer,
    AppRequest,
    Route,
    StandInApp,
    StandInStack,
)
from tests.mock_server_support import (
    GENEROUS_WAIT_S,
    StackClient,
    sample_document,
    write_config,
)
from tests.project_builders import project_meta

DATE = "2027-03-01"
ROOMS = [{"room": "oak", "slots": ["09:00", "10:00"]}]
AVAILABILITY = {
    "method": "GET",
    "path": "/availability",
    "query": {"date": DATE},
}
VENDOR_TARGET = f"/v1/rooms/availability?date={DATE}"
SHORT_LIMIT_MS = 100
"""A limit a test waits out: a test about a limit stays this strict."""
ANSWERABLE_LIMIT_MS = 500
"""A limit an app answers within, on a machine busy enough to take its time."""
RETRY_AFTER_HEADER = "retry-after"
FAST_POLL_S = 0.01
ANSWERED = AppAnswer(200, {})


def retrying_case() -> dict[str, Any]:
    """A 429 from the room vendor, then its answer: wait for Retry-After, then retry once."""
    return {
        "id": "h14",
        "level": 1,
        "mocks": {ROOM_VENDOR: "rate_limited_then_ok"},
        "request": AVAILABILITY,
        "expected": {"status": 200, "body": {"date": DATE, "rooms": ROOMS}},
        "log": [{"mock": ROOM_VENDOR, "route": "availability", "count": 2, "min_gap_ms": 950}],
    }


def case_of(document: dict[str, Any]) -> Case:
    """As the problem loader will read an entry of tests.json."""
    return Case(
        id=document["id"],
        input=http_case_input(document),
        expected=Expected(document["expected"]),
        visible=document.get("visible", False),
        level=document.get("level"),
        hang_guard_ms=document.get("hang_guard_ms"),
        note=document.get("note"),
    )


def simple_case(case_id: str, path: str, **fields: Any) -> dict[str, Any]:
    return {
        "id": case_id,
        "level": 1,
        "request": {"method": "GET", "path": path},
        "expected": {"status": 200},
        **fields,
    }


@pytest.fixture
def vendor(tmp_path: Path) -> Iterator[StackClient]:
    config = load_stack_config(write_config(tmp_path, sample_document()))
    servers = start_servers(config, ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield StackClient(servers.api_port, servers.control_port)
    servers.close()


@dataclass
class Graded:
    judgement: Judgement
    app: StandInApp
    stack: StandInStack

    @property
    def verdict(self) -> CaseVerdict:
        return self.judgement.verdicts[0]

    @property
    def statuses(self) -> list[CaseStatus]:
        return [verdict.status for verdict in self.judgement.verdicts]

    @property
    def reason(self) -> str | None:
        return self.verdict.mismatch.detail if self.verdict.mismatch else None


type Grade = Callable[..., Graded]


@pytest.fixture
def grade(vendor: StackClient) -> Iterator[Grade]:
    apps: list[StandInApp] = []

    def run(
        routes: Mapping[tuple[str, str], Route],
        *documents: dict[str, Any],
        restart_takes_s: float = 0.0,
    ) -> Graded:
        app = StandInApp(routes)
        apps.append(app)
        stack = StandInStack(app, vendor.control_port, restart_takes_s)
        meta = project_meta(comparator=ComparatorSpec(ComparatorType.EXACT))
        problem = Problem(meta, tuple(case_of(document) for document in documents))
        judgement = run_http_grading(
            HttpGradingRun(problem, 1, Config()), stack, open_stack_clients
        )
        return Graded(judgement, app, stack)

    yield run
    for app in apps:
        if app.exit is None:
            app.close()


def availability_from(vendor: StackClient, *, retry: Callable[[int], None]) -> Route:
    """Writes its keys in another order than a case's expected body does."""

    def route(request: AppRequest) -> AppAnswer:
        answer = vendor.api(f"/v1/rooms/availability?date={request.query['date']}")
        if answer.status == 429:
            retry(int(answer.headers[RETRY_AFTER_HEADER]))
            answer = vendor.api(f"/v1/rooms/availability?date={request.query['date']}")
        return AppAnswer(200, {"rooms": answer.document()["rooms"], "date": request.query["date"]})

    return route


def careful(vendor: StackClient) -> Route:
    """Waits for Retry-After."""
    return availability_from(vendor, retry=time.sleep)


def naive(vendor: StackClient) -> Route:
    """Retries at once."""
    return availability_from(vendor, retry=lambda _seconds: None)


def test_an_app_that_waits_for_retry_after_passes(grade: Grade, vendor: StackClient):
    graded = grade({("GET", "/availability"): careful(vendor)}, retrying_case())
    assert graded.statuses == [CaseStatus.PASS]


def test_a_naive_app_gets_the_right_answer_and_fails_on_its_log_gap(
    grade: Grade, vendor: StackClient
):
    graded = grade({("GET", "/availability"): naive(vendor)}, retrying_case())
    assert graded.statuses == [CaseStatus.FAIL]
    assert graded.reason is not None
    assert graded.reason.startswith(
        "room-vendor availability: expected at least 950 ms from response 1 to request 2, saw "
    )


def test_an_app_that_hammers_the_vendor_fails_on_its_count(grade: Grade, vendor: StackClient):
    def hammering(_request: AppRequest) -> AppAnswer:
        for _attempt in range(5):
            vendor.api(VENDOR_TARGET)
        return AppAnswer(503, {"error": "vendor unavailable"})

    document = simple_case(
        "h1",
        "/availability",
        mocks={ROOM_VENDOR: "rate_limited"},
        expected={"status": 503},
        log=[{"mock": ROOM_VENDOR, "route": "availability", "max_count": 2}],
    )
    graded = grade({("GET", "/availability"): hammering}, document)
    assert graded.reason == "room-vendor availability: expected at most 2 requests, saw 5"


def test_a_scenario_reaches_the_app_through_the_mock_server(grade: Grade, vendor: StackClient):
    def degrading(_request: AppRequest) -> AppAnswer:
        answer = vendor.api(VENDOR_TARGET)
        return AppAnswer(200, {"rooms": [], "vendor_status": answer.status})

    document = simple_case(
        "h1",
        "/availability",
        mocks={ROOM_VENDOR: "outage"},
        expected={"status": 200, "body": {"rooms": [], "vendor_status": 503}},
    )
    graded = grade({("GET", "/availability"): degrading}, document)
    assert graded.statuses == [CaseStatus.PASS]


def test_scenarios_and_logs_do_not_carry_over_between_cases(grade: Grade, vendor: StackClient):
    def passing_on(_request: AppRequest) -> AppAnswer:
        return AppAnswer(200, {"vendor_status": vendor.api(VENDOR_TARGET).status})

    first = simple_case(
        "h1",
        "/availability",
        mocks={ROOM_VENDOR: "outage"},
        expected={"status": 200, "body": {"vendor_status": 503}},
    )
    second = simple_case(
        "h2",
        "/availability",
        expected={"status": 200, "body": {"vendor_status": 200}},
        log=[{"mock": ROOM_VENDOR, "count": 1}],
    )
    graded = grade({("GET", "/availability"): passing_on}, first, second)
    assert graded.statuses == [CaseStatus.PASS, CaseStatus.PASS]


def booking_route(request: AppRequest) -> AppAnswer:
    try:
        member = json.loads(request.body)["member"]
    except json.JSONDecodeError:
        return AppAnswer(400, {"error": "malformed body"})
    return AppAnswer(201, {"booked": member})


def test_a_malformed_body_reaches_the_app_as_written(grade: Grade):
    document = {
        "id": "h1",
        "level": 1,
        "request": {
            "method": "POST",
            "path": "/bookings",
            "headers": {"Content-Type": "application/json"},
            "body": '{"member": ',
        },
        "expected": {"status": 400, "body": {"error": "malformed body"}},
    }
    assert grade({("POST", "/bookings"): booking_route}, document).statuses == [CaseStatus.PASS]


def test_a_json_body_reaches_the_app_as_json(grade: Grade):
    document = {
        "id": "h1",
        "level": 1,
        "request": {"method": "POST", "path": "/bookings", "json": {"member": "m1"}},
        "expected": {"status": 201, "body": {"booked": "m1"}},
    }
    assert grade({("POST", "/bookings"): booking_route}, document).statuses == [CaseStatus.PASS]


def test_an_app_that_answers_a_wrong_status_says_both(grade: Grade):
    document = simple_case("h1", "/a")
    graded = grade({("GET", "/a"): lambda _request: AppAnswer(500, {"error": "boom"})}, document)
    assert graded.reason == "status: expected 200, got 500"


def test_a_charset_on_the_content_type_cannot_fail_a_listed_header(grade: Grade):
    document = simple_case(
        "h1",
        "/a",
        expected={"status": 200, "headers": {"Content-Type": "application/json"}},
    )
    assert grade({("GET", "/a"): lambda _request: ANSWERED}, document).statuses == [CaseStatus.PASS]


def dying(request: AppRequest) -> None:
    request.app.die(137, "out of memory\n")


def answering(_request: AppRequest) -> AppAnswer:
    return ANSWERED


def hanging(request: AppRequest) -> None:
    request.app.stopping.wait(GENEROUS_WAIT_S)


DIES_MID_RUN: dict[tuple[str, str], Route] = {
    ("GET", "/ok"): answering,
    ("GET", "/dies"): dying,
}


def test_an_app_that_dies_says_so_and_the_rest_fail_fast(grade: Grade):
    cases = (simple_case("h1", "/ok"), simple_case("h2", "/dies"), simple_case("h3", "/ok"))
    graded = grade(DIES_MID_RUN, *cases)
    assert graded.statuses == [CaseStatus.PASS, CaseStatus.ERROR, CaseStatus.NOT_RUN]
    outcome = graded.judgement.verdicts[1].outcome
    assert isinstance(outcome, Raised)
    assert (outcome.error.type, outcome.error.message, outcome.error.trace) == (
        "AppExited",
        "the app exited with code 137 during this case",
        "out of memory\n",
    )


def test_nothing_is_sent_after_the_app_died(grade: Grade):
    cases = (simple_case("h1", "/dies"), simple_case("h2", "/ok"))
    assert grade(DIES_MID_RUN, *cases).app.requests == ["GET /dies"]


def test_an_app_that_hangs_times_out_at_the_cases_limit(grade: Grade):
    document = simple_case("h1", "/hangs", hang_guard_ms=SHORT_LIMIT_MS)
    graded = grade({("GET", "/hangs"): hanging}, document)
    assert (graded.statuses, graded.verdict.outcome) == (
        [CaseStatus.TIMEOUT],
        TimedOut(SHORT_LIMIT_MS),
    )


def test_a_hung_app_is_restarted_and_the_next_case_runs(grade: Grade):
    routes: dict[tuple[str, str], Route] = {("GET", "/hangs"): hanging, ("GET", "/ok"): answering}
    cases = (
        simple_case("h1", "/hangs", hang_guard_ms=SHORT_LIMIT_MS),
        simple_case("h2", "/ok"),
    )
    graded = grade(routes, *cases)
    assert (graded.statuses, graded.stack.restarts) == (
        [CaseStatus.TIMEOUT, CaseStatus.PASS],
        ["app"],
    )


def test_a_slow_fresh_restart_spends_none_of_the_cases_limit(grade: Grade):
    """The owner's rule: a limit starts once the stack is ready, and a restart is startup."""
    document = simple_case("h1", "/ok", fresh=True, hang_guard_ms=ANSWERABLE_LIMIT_MS)
    longer_than_the_limit_s = ANSWERABLE_LIMIT_MS * 1.2 / 1000
    graded = grade({("GET", "/ok"): answering}, document, restart_takes_s=longer_than_the_limit_s)
    assert (graded.statuses, graded.stack.restarts) == ([CaseStatus.PASS], ["fresh"])


def test_a_port_with_nothing_listening_is_a_refused_connection(grade: Grade):
    def closes_its_listener(request: AppRequest) -> AppAnswer:
        request.app.close()
        return ANSWERED

    routes: dict[tuple[str, str], Route] = {("GET", "/closes"): closes_its_listener}
    cases = (simple_case("h1", "/closes"), simple_case("h2", "/closes"))
    graded = grade(routes, *cases)
    outcome = graded.judgement.verdicts[1].outcome
    assert isinstance(outcome, Raised)
    assert outcome.error.type == "ConnectionRefused"


def test_a_failing_case_reaches_the_event_stream_in_todays_shape(grade: Grade, vendor: StackClient):
    graded = grade({("GET", "/availability"): naive(vendor)}, retrying_case())
    event = event_value(CaseGraded(graded.verdict, level=1))
    assert (event["type"], event["id"], event["status"], event["level"]) == (
        "case_result",
        "h14",
        "fail",
        1,
    )
    assert event["input"] == {**AVAILABILITY, "mocks": {ROOM_VENDOR: "rate_limited_then_ok"}}
    assert event["expected"] == retrying_case()["expected"]
    assert event["actual"] == {"status": 200, "body": {"rooms": ROOMS, "date": DATE}}
    assert event["reason"] == graded.reason


def test_a_failing_case_prints_through_todays_report(grade: Grade, vendor: StackClient):
    graded = grade({("GET", "/availability"): naive(vendor)}, retrying_case())
    details = dict(case_details(graded.verdict, None))
    assert details["reason"] == graded.reason
    assert 'path="/availability"' in details["input"]


def test_a_difference_past_the_report_cut_stays_in_the_reason(grade: Grade):
    rooms = [f"room-{index}" for index in range(100)]
    changed = [*rooms[:-1], "moved"]
    document = simple_case("h1", "/a", expected={"status": 200, "body": rooms})
    graded = grade({("GET", "/a"): lambda _request: AppAnswer(200, changed)}, document)
    assert graded.reason == 'body[99]: expected "room-99", got "moved"'
