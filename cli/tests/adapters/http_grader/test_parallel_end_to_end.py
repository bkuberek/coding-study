"""A parallel case graded end to end on loopback, with no container: the real clients send a burst
behind a barrier to a stand-in shop, and a case from a tests.json document judges what came back.

A shop that checks the stock and then updates it, with a database's round trip between the two,
must fail; the same shop holding a lock across both must pass, every run.
"""

import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any

import pytest

from coding_study.adapters.http_grader.clients import HttpAppClient, open_stack_clients
from coding_study.adapters.problem_documents import cases_from_document
from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.application.http_grading_ports import StackEndpoints
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.config import Config
from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from tests.adapters.http_grader.standin_app import AppAnswer, AppRequest, StandInApp, StandInStack
from tests.mock_server_support import GENEROUS_WAIT_S
from tests.project_builders import project_meta

STOCK = 3
CHECKOUTS = 10
ROUND_TRIP_S = 0.05
"""Between reading the stock and writing it back: what a query to a database costs, and far more
than the spread of a burst's arrivals, so a shop that does not lock oversells every time."""
UNUSED_CONTROL_PORT = 9
EXACT = ComparatorSpec(ComparatorType.EXACT)


def reservations_document() -> dict[str, Any]:
    return {
        "version": 1,
        "cases": [
            {
                "id": "h1",
                "level": 1,
                "fresh": True,
                "repeat": 3,
                "note": f"{CHECKOUTS} checkouts race for the last {STOCK} lamps",
                "before": [{"method": "POST", "path": "/restock"}],
                "parallel": {
                    "count": CHECKOUTS,
                    "request": {
                        "method": "POST",
                        "path": "/reservations",
                        "json": {"sku": "lamp", "order": "o{i}"},
                    },
                },
                "expected_statuses": {"201": STOCK, "409": CHECKOUTS - STOCK},
                "after": {
                    "request": {"method": "GET", "path": "/stock"},
                    "expected": {"status": 200, "body": {"stock": 0}},
                },
            }
        ],
    }


@dataclass
class Shop:
    """One item's stock, read and written in two steps with a round trip between them."""

    locking: bool
    stock: int = STOCK
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def restock(self, _request: AppRequest) -> AppAnswer:
        self.stock = STOCK
        return AppAnswer(200, {"stock": self.stock})

    def reserve(self, _request: AppRequest) -> AppAnswer:
        if not self.locking:
            return self._check_then_update()
        with self._lock:
            return self._check_then_update()

    def stock_left(self, _request: AppRequest) -> AppAnswer:
        return AppAnswer(200, {"stock": self.stock})

    def _check_then_update(self) -> AppAnswer:
        seen = self.stock
        time.sleep(ROUND_TRIP_S)
        if seen <= 0:
            return AppAnswer(409, {"error": "out of stock"})
        self.stock = seen - 1
        return AppAnswer(201, {"stock": self.stock})


class ShopStack(StandInStack):
    """A stack with no mock servers, so no control interface either."""

    @property
    def endpoints(self) -> StackEndpoints:
        return replace(super().endpoints, control_url=None)


@pytest.fixture
def apps() -> Iterator[list[StandInApp]]:
    started: list[StandInApp] = []
    yield started
    for app in started:
        app.close()


def graded(shop: Shop, apps: list[StandInApp]) -> CaseVerdict:
    app = StandInApp(
        {
            ("POST", "/restock"): shop.restock,
            ("POST", "/reservations"): shop.reserve,
            ("GET", "/stock"): shop.stock_left,
        }
    )
    apps.append(app)
    stack = ShopStack(app, UNUSED_CONTROL_PORT, mocks=())
    cases = cases_from_document(reservations_document(), EXACT, "tests.json")
    run = HttpGradingRun(Problem(project_meta(comparator=EXACT), cases), 1, Config())
    return run_http_grading(run, stack, open_stack_clients).verdicts[0]


def test_a_shop_that_checks_then_updates_oversells_and_fails(apps: list[StandInApp]):
    verdict = graded(Shop(locking=False), apps)

    assert verdict.status is CaseStatus.FAIL


def reason_of(verdict: CaseVerdict) -> str:
    return (verdict.mismatch and verdict.mismatch.detail) or ""


def test_the_oversold_shop_is_told_how_many_were_expected_to_succeed(apps: list[StandInApp]):
    reason = reason_of(graded(Shop(locking=False), apps))

    assert reason.startswith(
        f"run 1 of 3: {CHECKOUTS} requests at once: expected {STOCK} to answer 201 and "
        f"{CHECKOUTS - STOCK} to answer 409; "
    )


def test_the_oversold_shop_is_told_the_stock_it_left(apps: list[StandInApp]):
    reason = reason_of(graded(Shop(locking=False), apps))

    assert "after GET /stock: body.stock: expected 0, got " in reason


def test_a_shop_that_locks_passes_every_run(apps: list[StandInApp]):
    assert graded(Shop(locking=True), apps).status is CaseStatus.PASS


def test_requests_sent_together_are_all_in_flight_at_once(apps: list[StandInApp]):
    meeting = threading.Barrier(CHECKOUTS, timeout=GENEROUS_WAIT_S)

    def wait_for_the_others(_request: AppRequest) -> AppAnswer:
        try:
            meeting.wait()
        except threading.BrokenBarrierError:
            return AppAnswer(500, {"error": "the others never came"})
        return AppAnswer(200, {})

    app = StandInApp({("GET", "/meet"): wait_for_the_others})
    apps.append(app)
    client = HttpAppClient(f"http://127.0.0.1:{app.port}")
    limit_ms = int(GENEROUS_WAIT_S * 2_000)

    sent = client.send_together([HttpRequest("GET", "/meet")] * CHECKOUTS, limit_ms)

    assert [answer.status for answer in sent if isinstance(answer, HttpResponse)] == [
        200
    ] * CHECKOUTS


def test_nothing_sent_together_is_nothing_answered():
    assert HttpAppClient("http://127.0.0.1:9").send_together([], 100) == ()
