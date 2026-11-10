from dataclasses import dataclass, field

import pytest

from coding_study.application.http_grading import (
    APP_EXIT_GRACE_MS,
    MAX_HUNG_CASES,
    HttpGradingRun,
    run_http_grading,
)
from coding_study.application.http_grading_ports import AppExit
from coding_study.application.project_runs import project_levels
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected, FunctionInput
from coding_study.domain.config import Config, HangGuardSettings
from coding_study.domain.errors import ContentError
from coding_study.domain.http_case import HttpExpected, HttpRequest, LogAssertion, SameBody
from coding_study.domain.http_grading import (
    ExchangeFailed,
    ExchangeFailure,
    HttpResponse,
    LoggedRequest,
    MockLog,
)
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase
from coding_study.domain.precedence import DEFAULT_HANG_GUARD_MS
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from coding_study.domain.runs import NotRun, Raised, Returned, TimedOut
from coding_study.domain.submissions import level_tallies
from tests.application.http_grading_fakes import ROOM_VENDOR, Rig, http_case
from tests.project_builders import project_meta

EXACT = ComparatorSpec(ComparatorType.EXACT)
MILLISECONDS_NS = 1_000_000
TIMED_OUT = ExchangeFailed(ExchangeFailure.TIMED_OUT, "no answer within the limit")
REFUSED = ExchangeFailed(ExchangeFailure.REFUSED, "connection refused at /a")
DROPPED = ExchangeFailed(ExchangeFailure.DROPPED, "the connection was dropped")
NOT_HTTP = ExchangeFailed(ExchangeFailure.NOT_HTTP, "this answer is not HTTP", 5)
TOO_LARGE = ExchangeFailed(ExchangeFailure.TOO_LARGE, "this answer is too large", 6)
DIED = AppExit(137, "out of memory\n")


def problem_of(*cases: Case, comparator: ComparatorSpec = EXACT) -> Problem:
    return Problem(project_meta(comparator=comparator), cases)


def grade(rig: Rig, *cases: Case, config: Config | None = None, level: int = 2) -> Judgement:
    run = HttpGradingRun(problem_of(*cases), level, config or Config())
    return run_http_grading(run, rig.stack, rig.open_clients)


def statuses(judgement: Judgement) -> list[CaseStatus]:
    return [verdict.status for verdict in judgement.verdicts]


def reason_of(verdict: CaseVerdict) -> str | None:
    return verdict.mismatch.detail if verdict.mismatch else None


@dataclass
class HeardEvents:
    events: list[str] = field(default_factory=list[str])

    def case_started(self, case: RunnableCase) -> None:
        self.events.append(f"start {case.id}")

    def case_judged(self, verdict: CaseVerdict) -> None:
        self.events.append(f"{verdict.status.name} {verdict.case.id}")


def test_a_case_resets_the_mocks_sets_scenarios_sends_and_then_reads_the_log():
    rig = Rig()
    case = http_case(
        mocks={ROOM_VENDOR: "outage"},
        log=(LogAssertion(ROOM_VENDOR, count=0),),
    )
    grade(rig, case)
    assert rig.journal == [
        "mocks reset",
        f"scenario {ROOM_VENDOR}=outage",
        "send GET /a",
        f"log {ROOM_VENDOR}",
    ]


def test_each_case_starts_from_a_mock_reset():
    rig = Rig()
    grade(rig, http_case("h1"), http_case("h2"))
    assert rig.journal.count("mocks reset") == 2


def test_two_assertions_on_one_mock_server_read_its_log_once():
    rig = Rig()
    log = (LogAssertion(ROOM_VENDOR, count=0), LogAssertion(ROOM_VENDOR, max_count=1))
    grade(rig, http_case(log=log))
    assert rig.journal.count(f"log {ROOM_VENDOR}") == 1


def test_a_log_is_read_only_for_a_case_that_asserts_on_it():
    rig = Rig()
    grade(rig, http_case())
    assert not any(step.startswith("log") for step in rig.journal)


def test_a_fresh_case_restarts_before_its_scenarios_and_forgets_what_startup_called():
    rig = Rig()
    grade(rig, http_case(fresh=True, mocks={ROOM_VENDOR: "outage"}))
    assert rig.journal == [
        "mocks reset",
        "restart app with fresh data",
        "mocks reset",
        f"scenario {ROOM_VENDOR}=outage",
        "send GET /a",
    ]


def test_a_right_answer_passes():
    rig = Rig()
    assert statuses(grade(rig, http_case())) == [CaseStatus.PASS]


def test_a_wrong_answer_fails_with_the_difference():
    rig = Rig()
    rig.app.answers["/a"] = HttpResponse(503, {}, b"")
    verdict = grade(rig, http_case()).verdicts[0]
    assert (verdict.status, reason_of(verdict)) == (
        CaseStatus.FAIL,
        "status: expected 200, got 503",
    )


def test_a_passing_answer_with_a_wrong_log_fails_on_the_log():
    rig = Rig()
    rig.control.logs[ROOM_VENDOR] = MockLog((LoggedRequest("r", 0, 1), LoggedRequest("r", 2, 3)))
    case = http_case(log=(LogAssertion(ROOM_VENDOR, "r", count=1),))
    verdict = grade(rig, case).verdicts[0]
    assert (verdict.status, reason_of(verdict)) == (
        CaseStatus.FAIL,
        "room-vendor r: expected 1 request, saw 2",
    )


def test_the_case_comparator_overrides_the_problems():
    rig = Rig()
    rig.app.answers["/a"] = HttpResponse(200, {}, b"[2, 1]")
    expected = HttpExpected(200, Expected([1, 2]))
    case = http_case(expected=expected, comparator=ComparatorSpec(ComparatorType.UNORDERED))
    assert statuses(grade(rig, case)) == [CaseStatus.PASS]


def test_the_problems_comparator_applies_otherwise():
    rig = Rig()
    rig.app.answers["/a"] = HttpResponse(200, {}, b"[2, 1]")
    case = http_case(expected=HttpExpected(200, Expected([1, 2])))
    assert statuses(grade(rig, case)) == [CaseStatus.FAIL]


def test_before_requests_go_first():
    rig = Rig()
    grade(rig, http_case(before=(HttpRequest("POST", "/seed"),)))
    assert rig.journal[-2:] == ["send POST /seed", "send GET /a"]


def test_a_before_request_that_fails_stops_the_case():
    rig = Rig()
    rig.app.answers["/seed"] = HttpResponse(500, {}, b"")
    verdict = grade(rig, http_case(before=(HttpRequest("POST", "/seed"),))).verdicts[0]
    assert (verdict.status, reason_of(verdict), rig.journal[-1]) == (
        CaseStatus.FAIL,
        "before[0] POST /seed: expected a 2xx status, got 500",
        "send POST /seed",
    )


def test_a_case_is_limited_by_the_default_hang_guard():
    rig = Rig()
    grade(rig, http_case())
    assert rig.app.limits == [DEFAULT_HANG_GUARD_MS]


def test_a_case_may_set_its_own_limit():
    rig = Rig()
    grade(rig, http_case(hang_guard_ms=250))
    assert rig.app.limits == [250]


def test_config_wins_over_the_case_as_for_a_runner():
    rig = Rig()
    grade(rig, http_case(hang_guard_ms=250), config=Config(hang_guard=HangGuardSettings(ms=900)))
    assert rig.app.limits == [900]


def test_before_requests_spend_the_same_limit():
    rig = Rig()
    rig.app.answers["/seed"] = HttpResponse(200, {}, b"", duration_ns=100 * MILLISECONDS_NS)
    grade(rig, http_case(hang_guard_ms=250, before=(HttpRequest("POST", "/seed"),)))
    assert rig.app.limits == [250, 150]


def test_a_before_request_that_spends_the_whole_limit_times_the_case_out():
    rig = Rig()
    rig.app.answers["/seed"] = HttpResponse(200, {}, b"", duration_ns=300 * MILLISECONDS_NS)
    rig.app.answers["/a"] = TIMED_OUT
    verdict = grade(rig, http_case(hang_guard_ms=250, before=(HttpRequest("POST", "/seed"),)))
    assert (verdict.verdicts[0].status, rig.app.limits) == (CaseStatus.TIMEOUT, [250, 0])


def test_a_timeout_is_a_timeout_with_its_limit():
    rig = Rig()
    rig.app.answers["/a"] = TIMED_OUT
    verdict = grade(rig, http_case(hang_guard_ms=250)).verdicts[0]
    assert (verdict.status, verdict.outcome) == (CaseStatus.TIMEOUT, TimedOut(250))


def test_a_timeout_restarts_the_app_for_the_next_case():
    rig = Rig()
    rig.app.answers["/hung"] = TIMED_OUT
    judgement = grade(rig, http_case("h1", path="/hung"), http_case("h2", path="/b"))
    assert "restart app" in rig.journal
    assert statuses(judgement) == [CaseStatus.TIMEOUT, CaseStatus.PASS]


def test_a_timeout_does_not_read_the_log():
    rig = Rig()
    rig.app.answers["/a"] = TIMED_OUT
    grade(rig, http_case(log=(LogAssertion(ROOM_VENDOR, count=1),)))
    assert f"log {ROOM_VENDOR}" not in rig.journal


def test_the_app_hanging_too_often_leaves_the_rest_not_run():
    rig = Rig()
    hung = [f"/hung{index}" for index in range(MAX_HUNG_CASES)]
    rig.app.answers |= dict.fromkeys(hung, TIMED_OUT)
    cases = [http_case(f"h{index}", path=path) for index, path in enumerate(hung)]
    judgement = grade(rig, *cases, http_case("last", path="/b"))
    assert statuses(judgement) == [*[CaseStatus.TIMEOUT] * MAX_HUNG_CASES, CaseStatus.NOT_RUN]


def test_the_last_hung_case_needs_no_restart():
    rig = Rig()
    hung = [f"/hung{index}" for index in range(MAX_HUNG_CASES)]
    rig.app.answers |= dict.fromkeys(hung, TIMED_OUT)
    grade(rig, *(http_case(f"h{index}", path=path) for index, path in enumerate(hung)))
    assert rig.journal.count("restart app") == MAX_HUNG_CASES - 1


def test_a_restart_that_fails_leaves_the_rest_not_run():
    rig = Rig()
    rig.stack.restart_problem = "the app did not answer its health path"
    rig.app.answers["/hung"] = TIMED_OUT
    judgement = grade(rig, http_case("h1", path="/hung"), http_case("h2", path="/b"))
    assert statuses(judgement) == [CaseStatus.TIMEOUT, CaseStatus.NOT_RUN]


def test_a_timeout_with_the_app_gone_says_the_app_died():
    rig = Rig()
    rig.stack.exit = DIED
    rig.app.answers["/a"] = TIMED_OUT
    verdict = grade(rig, http_case()).verdicts[0]
    assert (verdict.status, isinstance(verdict.outcome, Raised)) == (CaseStatus.ERROR, True)


def test_connection_refused_is_an_error_that_says_so():
    rig = Rig()
    rig.app.answers["/a"] = REFUSED
    verdict = grade(rig, http_case()).verdicts[0]
    assert verdict.status is CaseStatus.ERROR
    assert isinstance(verdict.outcome, Raised)
    assert (verdict.outcome.error.type, verdict.outcome.error.message) == (
        "ConnectionRefused",
        REFUSED.detail,
    )


def test_a_refused_connection_with_the_app_running_lets_the_next_case_try():
    rig = Rig()
    rig.app.answers["/down"] = REFUSED
    judgement = grade(rig, http_case("h1", path="/down"), http_case("h2", path="/b"))
    assert statuses(judgement) == [CaseStatus.ERROR, CaseStatus.PASS]


def test_a_dropped_connection_is_an_error_that_says_so():
    rig = Rig()
    rig.app.answers["/a"] = DROPPED
    verdict = grade(rig, http_case()).verdicts[0]
    assert isinstance(verdict.outcome, Raised)
    assert verdict.outcome.error.type == "ConnectionDropped"


def test_a_failed_connection_gives_a_dying_app_a_moment_to_show_its_exit():
    rig = Rig()
    rig.app.answers["/a"] = DROPPED
    grade(rig, http_case())
    assert rig.stack.exit_waits == [APP_EXIT_GRACE_MS]


def test_an_app_that_died_says_so_with_its_exit_code_and_stderr():
    rig = Rig()
    rig.stack.exit = DIED
    rig.app.answers["/a"] = DROPPED
    verdict = grade(rig, http_case()).verdicts[0]
    assert verdict.status is CaseStatus.ERROR
    assert isinstance(verdict.outcome, Raised)
    assert (
        verdict.outcome.error.type,
        verdict.outcome.error.message,
        verdict.outcome.error.trace,
    ) == ("AppExited", "the app exited with code 137 during this case", "out of memory\n")


def test_the_cases_after_an_app_died_fail_fast_and_send_nothing():
    rig = Rig()
    rig.stack.exit = DIED
    rig.app.answers["/dies"] = DROPPED
    judgement = grade(rig, http_case("h1", path="/dies"), http_case("h2", path="/b"))
    assert statuses(judgement) == [CaseStatus.ERROR, CaseStatus.NOT_RUN]
    assert "send GET /b" not in rig.journal


def test_a_case_not_run_says_why_without_naming_the_hidden_case_that_failed():
    rig = Rig()
    rig.stack.exit = DIED
    rig.app.answers["/dies"] = DROPPED
    judgement = grade(rig, http_case("secret", path="/dies"), http_case("h2", path="/b"))
    assert judgement.verdicts[1].outcome == NotRun(
        "the app exited with code 137 during an earlier case"
    )


def test_an_answer_that_is_not_http_is_invalid_and_the_run_goes_on():
    rig = Rig()
    rig.app.answers["/bad"] = NOT_HTTP
    judgement = grade(rig, http_case("h1", path="/bad"), http_case("h2", path="/b"))
    assert statuses(judgement) == [CaseStatus.INVALID, CaseStatus.PASS]


def test_an_answer_too_large_to_keep_is_invalid():
    rig = Rig()
    rig.app.answers["/a"] = TOO_LARGE
    assert statuses(grade(rig, http_case())) == [CaseStatus.INVALID]


def test_a_reset_that_fails_is_an_error_with_its_output():
    rig = Rig()
    rig.stack.restart_problem = "commands.reset exited with code 1"
    verdict = grade(rig, http_case(fresh=True)).verdicts[0]
    assert verdict.status is CaseStatus.ERROR
    assert isinstance(verdict.outcome, Raised)
    assert (verdict.outcome.error.message, verdict.outcome.error.trace) == (
        "commands.reset exited with code 1",
        "output of the reset",
    )


def test_a_reset_that_fails_leaves_the_rest_not_run():
    rig = Rig()
    rig.stack.restart_problem = "commands.reset exited with code 1"
    judgement = grade(rig, http_case("h1", fresh=True), http_case("h2"))
    assert statuses(judgement) == [CaseStatus.ERROR, CaseStatus.NOT_RUN]


def test_the_listener_hears_each_case_start_and_end():
    rig = Rig()
    heard = HeardEvents()
    run = HttpGradingRun(problem_of(http_case("h1"), http_case("h2")), 1, Config(), heard)
    run_http_grading(run, rig.stack, rig.open_clients)
    assert heard.events == ["start h1", "PASS h1", "start h2", "PASS h2"]


def test_the_listener_hears_a_case_not_run_with_no_start():
    rig = Rig()
    rig.stack.exit = DIED
    rig.app.answers["/dies"] = DROPPED
    heard = HeardEvents()
    cases = (http_case("h1", path="/dies"), http_case("h2"))
    run_http_grading(
        HttpGradingRun(problem_of(*cases), 1, Config(), heard), rig.stack, rig.open_clients
    )
    assert heard.events == ["start h1", "ERROR h1", "NOT_RUN h2"]


def test_a_right_answer_reports_how_long_it_took():
    rig = Rig()
    rig.app.answers["/a"] = HttpResponse(200, {}, b"", duration_ns=42)
    outcome = grade(rig, http_case()).verdicts[0].outcome
    assert isinstance(outcome, Returned)
    assert outcome.duration_ns == 42


def test_only_the_cases_up_to_the_level_run():
    rig = Rig()
    judgement = grade(rig, http_case("h1"), http_case("h2", path="/b", level=2), level=1)
    assert (judgement.case_count, rig.app.limits) == (1, [DEFAULT_HANG_GUARD_MS])


def test_a_judgement_counts_per_level_with_the_tallies_of_todays_submit():
    rig = Rig()
    rig.app.answers["/b"] = HttpResponse(500, {}, b"")
    cases = (http_case("ex1", visible=True), http_case("h2", path="/b", level=2))
    judgement = grade(rig, *cases)
    tallies = level_tallies(cases, judgement)
    assert [(t.level, t.all_passed) for t in tallies] == [(1, True), (2, False)]


def test_a_pass_of_the_unlocked_level_opens_the_next_as_todays_submit_does():
    rig = Rig()
    problem = problem_of(http_case("h1"), http_case("h2", path="/b", level=2))
    levels = project_levels(problem.meta, 1, None)
    judgement = run_http_grading(
        HttpGradingRun(problem, levels.ran_up_to, Config()), rig.stack, rig.open_clients
    )
    assert judgement.passed
    assert levels.after_passing().newly_unlocked


def test_a_regrade_of_a_lower_level_opens_nothing():
    rig = Rig()
    problem = problem_of(http_case("h1"), http_case("h2", path="/b", level=2))
    levels = project_levels(problem.meta, 2, 1)
    judgement = run_http_grading(
        HttpGradingRun(problem, levels.ran_up_to, Config()), rig.stack, rig.open_clients
    )
    assert (judgement.case_count, levels.after_passing().newly_unlocked) == (1, False)


def test_a_case_that_is_not_an_http_case_is_a_content_error_before_any_request():
    rig = Rig()
    with pytest.raises(ContentError, match="h1"):
        grade(rig, Case("h1", FunctionInput({}), Expected(1), level=1))
    assert rig.journal == []


def test_a_scenario_on_an_unknown_mock_server_is_a_content_error_before_any_request():
    rig = Rig()
    with pytest.raises(ContentError, match="other-vendor"):
        grade(rig, http_case(mocks={"other-vendor": "outage"}))
    assert rig.journal == []


def test_a_log_assertion_on_an_unknown_mock_server_is_a_content_error():
    rig = Rig()
    with pytest.raises(ContentError, match="other-vendor"):
        grade(rig, http_case(log=(LogAssertion("other-vendor", count=1),)))


def test_a_same_body_reference_to_an_unknown_mock_server_is_a_content_error():
    rig = Rig()
    same = SameBody("other-vendor", None, ("messages",))
    with pytest.raises(ContentError, match="other-vendor"):
        grade(rig, http_case(log=(LogAssertion(ROOM_VENDOR, count=1, body_same_as=same),)))


def test_a_same_body_assertion_reads_its_reference_log():
    rig = Rig()
    rig.control.logs[ROOM_VENDOR] = MockLog((LoggedRequest("r", 0, 1, {}, '{"m": [1]}'),))
    same = SameBody(ROOM_VENDOR, "r", ("m",))
    case = http_case(log=(LogAssertion(ROOM_VENDOR, "r", count=1, body_same_as=same),))
    assert statuses(grade(rig, case)) == [CaseStatus.PASS]


def test_an_unknown_scenario_is_a_content_error_that_keeps_its_name_out_of_a_report():
    rig = Rig()
    rig.control.unknown_scenarios = frozenset({"hidden-name"})
    with pytest.raises(ContentError, match=ROOM_VENDOR) as raised:
        grade(rig, http_case(mocks={ROOM_VENDOR: "hidden-name"}))
    assert "hidden-name" not in str(raised.value)


@pytest.mark.parametrize("comparator", [ComparatorType.CHECKER, ComparatorType.OPS])
def test_a_comparator_that_cannot_judge_a_body_is_a_content_error(comparator: ComparatorType):
    rig = Rig()
    run = HttpGradingRun(
        problem_of(http_case(), comparator=ComparatorSpec(comparator)), 1, Config()
    )
    with pytest.raises(ContentError, match="comparator"):
        run_http_grading(run, rig.stack, rig.open_clients)
