"""test-doubles promises that its hidden cases catch the classic mistakes of a small test-double
library: rules searched oldest first or advanced when shadowed, sequences that wrap, patterns that
ignore length, spies that count or index wrongly or reuse a call for two steps, mocks that try
the wrong expectation first, forget to report an unexpected call or report it in the wrong order,
and fake clocks that break ties by id, stop short of the end of an advance or bypass the double.
These tests replay every case against a model of the library written from the statement, which
must give every expected output, and against that model with one mistake planted at a time,
which some hidden case must fail. A mistake that crashes fails its case, as a thrown exception
does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0354-test-doubles"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]


class Model:
    """The library as the statement words it. Every double is a dict, every call an entry of
    one list, and the waiting timers a plain list searched for the smallest key on each firing,
    so that each mistake below overrides a single method."""

    def __init__(self) -> None:
        self.doubles: dict[str, dict[str, Any]] = {}
        self.calls: list[dict[str, Any]] = []
        self.clock = 0
        self.timers: list[dict[str, Any]] = []
        self.queue: list[dict[str, Any]] = []
        self.queued = 0

    # --- matching
    def fits(self, pattern: list[str], args: list[str]) -> bool:
        if len(pattern) != len(args):
            return False
        return all(want in ("*", got) for want, got in zip(pattern, args, strict=True))

    def count_fits(self, pattern: list[str], args: list[str]) -> bool:
        return self.fits(pattern, args)

    # --- level 1
    def create(self, name: str, kind: str, strict: bool) -> bool:
        if name in self.doubles:
            return False
        self.doubles[name] = {
            "kind": kind,
            "strict": strict,
            "rules": [],
            "otherwise": {},
            "expected": [],
            "surprises": [],
        }
        return True

    def add_stub(self, name: str) -> bool:
        return self.create(name, "stub", False)

    def on_call(self, name: str, method: str, args: list[str], answers: list[str]) -> bool:
        if name not in self.doubles:
            return False
        rule = {"method": method, "pattern": args, "answers": answers, "used": 0}
        self.doubles[name]["rules"].append(rule)
        return True

    def otherwise(self, name: str, method: str, answer: str) -> bool:
        if name not in self.doubles:
            return False
        self.doubles[name]["otherwise"][method] = answer
        return True

    def rule_order(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(reversed(rules))

    def pick(self, rule: dict[str, Any]) -> str:
        answers = rule["answers"]
        answer = answers[min(rule["used"], len(answers) - 1)]
        rule["used"] += 1
        return answer

    def stub_answer(self, double: dict[str, Any], method: str, args: list[str]) -> str | None:
        for rule in self.rule_order(double["rules"]):
            if rule["method"] == method and self.fits(rule["pattern"], args):
                return self.pick(rule)
        return double["otherwise"].get(method)

    def unknown_answer(self) -> str:
        return "!unknown"

    def call(self, name: str, method: str, args: list[str]) -> str:
        double = self.doubles.get(name)
        if double is None:
            return self.unknown_answer()
        self.record(name, method, args)
        if double["kind"] == "mock":
            return self.mock_answer(name, double, method, args)
        answer = self.stub_answer(double, method, args)
        return "" if answer is None else answer

    def record(self, name: str, method: str, args: list[str]) -> None:
        self.calls.append({"name": name, "method": method, "args": list(args), "at": self.clock})

    # --- level 2
    def calls_of(self, name: str) -> list[dict[str, Any]]:
        return [call for call in self.calls if call["name"] == name]

    def call_count(self, name: str, method: str) -> int:
        if name not in self.doubles:
            return -1
        return sum(call["method"] == method for call in self.calls_of(name))

    def match_count(self, name: str, method: str, args: list[str]) -> int:
        if name not in self.doubles:
            return -1
        return sum(
            call["method"] == method and self.count_fits(args, call["args"])
            for call in self.calls_of(name)
        )

    def nth_call(self, name: str, n: int) -> list[str]:
        mine = self.calls_of(name) if name in self.doubles else []
        if n >= 1 and n <= len(mine):
            chosen = mine[n - 1]
        elif n <= -1 and -n <= len(mine):
            chosen = mine[len(mine) + n]
        else:
            return []
        return [chosen["method"], *chosen["args"]]

    def in_order(self, steps: list[list[str]]) -> bool:
        position = 0
        for step in steps:
            while position < len(self.calls) and not self.step_fits(step, self.calls[position]):
                position += 1
            if position == len(self.calls):
                return False
            position += 1
        return True

    def step_fits(self, step: list[str], call: dict[str, Any]) -> bool:
        return (
            step[0] == call["name"]
            and step[1] == call["method"]
            and self.fits(step[2:], call["args"])
        )

    # --- level 3
    def add_mock(self, name: str, strict: bool) -> bool:
        return self.create(name, "mock", strict)

    def expect(self, name: str, method: str, args: list[str], answer: str, times: int) -> bool:
        double = self.doubles.get(name)
        if double is None or double["kind"] != "mock":
            return False
        double["expected"].append(
            {"method": method, "pattern": args, "answer": answer, "times": times, "got": 0}
        )
        return True

    def expectation_order(self, expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return expected

    def has_room(self, expectation: dict[str, Any]) -> bool:
        return expectation["got"] < expectation["times"]

    def mock_answer(self, name: str, double: dict[str, Any], method: str, args: list[str]) -> str:
        for expectation in self.expectation_order(double["expected"]):
            if (
                expectation["method"] == method
                and self.has_room(expectation)
                and self.fits(expectation["pattern"], args)
            ):
                expectation["got"] += 1
                return expectation["answer"]
        allowed = self.stub_answer(double, method, args)
        if allowed is not None:
            return allowed
        return self.surprise(double, method, args)

    def surprise(self, double: dict[str, Any], method: str, args: list[str]) -> str:
        double["surprises"].append((method, list(args)))
        return "!unexpected" if double["strict"] else ""

    def missing_line(self, name: str, expectation: dict[str, Any]) -> str:
        pattern = ",".join(expectation["pattern"])
        got, times = expectation["got"], expectation["times"]
        return f"missing {name}.{expectation['method']}({pattern}) {got}/{times}"

    def verify(self, name: str) -> list[str]:
        double = self.doubles.get(name)
        if double is None:
            return ["!unknown"]
        missing = [self.missing_line(name, e) for e in double["expected"] if e["got"] < e["times"]]
        surprises = [
            f"unexpected {name}.{method}({','.join(args)})" for method, args in double["surprises"]
        ]
        return missing + surprises

    def mock_names(self) -> list[str]:
        return [name for name, double in self.doubles.items() if double["kind"] == "mock"]

    def verify_all(self) -> list[str]:
        return [line for name in self.mock_names() for line in self.verify(name)]

    # --- level 4
    def now(self) -> int:
        return self.clock

    def queue_up(self, timer: dict[str, Any], due: int) -> None:
        self.queued += 1
        self.queue.append({"timer": timer, "due": due, "order": self.queued})

    def make_timer(self, delay: int, every: int, name: str, method: str, args: list[str]) -> int:
        if name not in self.doubles:
            return -1
        timer = {"id": len(self.timers) + 1, "name": name, "method": method, "args": list(args)}
        timer.update({"every": every, "live": True})
        self.timers.append(timer)
        self.queue_up(timer, self.clock + delay)
        return timer["id"]

    def schedule(self, delay: int, name: str, method: str, args: list[str]) -> int:
        return self.make_timer(delay, 0, name, method, args)

    def every(self, interval: int, name: str, method: str, args: list[str]) -> int:
        return self.make_timer(interval, interval, name, method, args)

    def cancel(self, timer_id: int) -> bool:
        for timer in self.timers:
            if timer["id"] == timer_id and timer["live"]:
                timer["live"] = False
                return True
        return False

    def firing_key(self, entry: dict[str, Any]) -> tuple[int, int]:
        return (entry["due"], entry["order"])

    def due_by(self, entry: dict[str, Any], end: int) -> bool:
        return entry["due"] <= end

    def fire(self, timer: dict[str, Any], due: int) -> None:
        self.clock = due
        self.call(timer["name"], timer["method"], timer["args"])

    def finish(self, end: int) -> None:
        self.clock = end

    def advance(self, ms: int) -> list[str]:
        end = self.clock + ms
        fired = []
        while True:
            self.queue = [entry for entry in self.queue if entry["timer"]["live"]]
            ready = [entry for entry in self.queue if self.due_by(entry, end)]
            if not ready:
                break
            entry = min(ready, key=self.firing_key)
            self.queue.remove(entry)
            timer = entry["timer"]
            if timer["every"]:
                self.queue_up(timer, entry["due"] + timer["every"])
            else:
                timer["live"] = False
            fired.append(f"{timer['id']}@{entry['due']}")
            self.fire(timer, entry["due"])
        self.finish(end)
        return fired

    def pending(self) -> list[str]:
        live = [entry for entry in self.queue if entry["timer"]["live"]]
        return [f"{e['timer']['id']}@{e['due']}" for e in sorted(live, key=self.firing_key)]

    def call_times(self, name: str, method: str) -> list[int]:
        return [call["at"] for call in self.calls_of(name) if call["method"] == method]


class OldestRuleWins(Model):
    """Searches the stub rules from the oldest instead of the newest."""

    def rule_order(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(rules)


class ShadowedRulesAdvance(Model):
    """Moves the counter of every rule that fits, not only of the one that answers."""

    def stub_answer(self, double: dict[str, Any], method: str, args: list[str]) -> str | None:
        fitting = [
            rule
            for rule in self.rule_order(double["rules"])
            if rule["method"] == method and self.fits(rule["pattern"], args)
        ]
        if not fitting:
            return double["otherwise"].get(method)
        answer = self.pick(fitting[0])
        for rule in fitting[1:]:
            rule["used"] += 1
        return answer


class AnswersWrapAround(Model):
    """Starts the list of answers again after the last one, instead of repeating it."""

    def pick(self, rule: dict[str, Any]) -> str:
        answer = rule["answers"][rule["used"] % len(rule["answers"])]
        rule["used"] += 1
        return answer


class OtherwiseBeforeRules(Model):
    """Lets the otherwise answer win over the rules."""

    def stub_answer(self, double: dict[str, Any], method: str, args: list[str]) -> str | None:
        if method in double["otherwise"]:
            return double["otherwise"][method]
        return super().stub_answer(double, method, args)


class PatternIgnoresLength(Model):
    """Compares a pattern with as many arguments as both have."""

    def fits(self, pattern: list[str], args: list[str]) -> bool:
        return all(want in ("*", got) for want, got in zip(pattern, args, strict=False))


class UnknownDoubleAnswersEmpty(Model):
    """Answers a call to a missing double like a stub with no rules."""

    def unknown_answer(self) -> str:
        return ""


class SecondStubReplacesFirst(Model):
    """Lets a new double take a name that is in use."""

    def create(self, name: str, kind: str, strict: bool) -> bool:
        self.doubles.pop(name, None)
        return super().create(name, kind, strict)


class CountsEveryMethod(Model):
    """Counts the double's calls to any method."""

    def call_count(self, name: str, method: str) -> int:
        return len(self.calls_of(name)) if name in self.doubles else -1


class MissingDoubleCountsZero(Model):
    """Answers 0, not -1, for a name that no double has."""

    def call_count(self, name: str, method: str) -> int:
        return max(super().call_count(name, method), 0)


class CountPatternIgnoresLength(Model):
    """Counts a call when the pattern fits a prefix of its arguments."""

    def count_fits(self, pattern: list[str], args: list[str]) -> bool:
        return all(want in ("*", got) for want, got in zip(pattern, args, strict=False))


class NthCallFromZero(Model):
    """Counts `n` from zero."""

    def nth_call(self, name: str, n: int) -> list[str]:
        return super().nth_call(name, n + 1 if n >= 0 else n)


class NegativeNthFromTheFront(Model):
    """Reads a negative `n` as a position from the first call."""

    def nth_call(self, name: str, n: int) -> list[str]:
        return super().nth_call(name, -n if n < 0 else n)


class OneCallServesManySteps(Model):
    """Lets one call fit several steps in a row."""

    def in_order(self, steps: list[list[str]]) -> bool:
        position = 0
        for step in steps:
            while position < len(self.calls) and not self.step_fits(step, self.calls[position]):
                position += 1
            if position == len(self.calls):
                return False
        return True


class OrderIgnored(Model):
    """Checks only that every step has a call somewhere."""

    def in_order(self, steps: list[list[str]]) -> bool:
        return all(any(self.step_fits(step, call) for call in self.calls) for step in steps)


class NewestExpectationFirst(Model):
    """Tries the newest expectation first."""

    def expectation_order(self, expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(reversed(expected))


class ExpectationsNeverRunOut(Model):
    """Lets an expectation take calls beyond its count."""

    def has_room(self, expectation: dict[str, Any]) -> bool:
        return True


class StubRulesBeforeExpectations(Model):
    """Lets a stub rule answer before the expectations are tried."""

    def mock_answer(self, name: str, double: dict[str, Any], method: str, args: list[str]) -> str:
        for rule in self.rule_order(double["rules"]):
            if rule["method"] == method and self.fits(rule["pattern"], args):
                return self.pick(rule)
        return super().mock_answer(name, double, method, args)


class StrictMockAnswersEmpty(Model):
    """Lets a strict mock answer an unexpected call with the empty answer."""

    def surprise(self, double: dict[str, Any], method: str, args: list[str]) -> str:
        double["surprises"].append((method, list(args)))
        return ""


class LenientMockForgets(Model):
    """Does not report the unexpected calls of a lenient mock."""

    def surprise(self, double: dict[str, Any], method: str, args: list[str]) -> str:
        if double["strict"]:
            return super().surprise(double, method, args)
        return ""


class StrictMockForgets(Model):
    """Reports an unexpected call of a strict mock at the call but not in the final check."""

    def surprise(self, double: dict[str, Any], method: str, args: list[str]) -> str:
        if double["strict"]:
            return "!unexpected"
        return super().surprise(double, method, args)


class OtherwiseIsNoAllowance(Model):
    """Ignores the otherwise answer on a mock, so the call is unexpected."""

    def mock_answer(self, name: str, double: dict[str, Any], method: str, args: list[str]) -> str:
        saved = double["otherwise"]
        double["otherwise"] = {}
        try:
            return super().mock_answer(name, double, method, args)
        finally:
            double["otherwise"] = saved


class UnexpectedBeforeMissing(Model):
    """Lists the unexpected calls before the missing expectations."""

    def verify(self, name: str) -> list[str]:
        lines = super().verify(name)
        return sorted(lines, key=lambda line: not line.startswith("unexpected"))


class MissingShowsCallsLeft(Model):
    """Writes the calls still owed instead of the calls received."""

    def missing_line(self, name: str, expectation: dict[str, Any]) -> str:
        pattern = ",".join(expectation["pattern"])
        left = expectation["times"] - expectation["got"]
        return f"missing {name}.{expectation['method']}({pattern}) {left}/{expectation['times']}"


class VerifyUnknownPasses(Model):
    """Checks a misspelled name and finds nothing wrong."""

    def verify(self, name: str) -> list[str]:
        return super().verify(name) if name in self.doubles else []


class StubsTakeExpectations(Model):
    """Accepts an expectation on a stub."""

    def expect(self, name: str, method: str, args: list[str], answer: str, times: int) -> bool:
        if name in self.doubles and self.doubles[name]["kind"] == "stub":
            self.doubles[name]["kind"] = "mock"
        return super().expect(name, method, args, answer, times)


class MocksByName(Model):
    """Checks the mocks in the order of their names."""

    def mock_names(self) -> list[str]:
        return sorted(super().mock_names())


class TiesByTimerId(Model):
    """Breaks a tie by the timer's id instead of the order it was put in line."""

    def firing_key(self, entry: dict[str, Any]) -> tuple[int, int]:
        return (entry["due"], entry["timer"]["id"])


class EndOfAdvanceExcluded(Model):
    """Leaves a timer due exactly at the end of an advance for later."""

    def due_by(self, entry: dict[str, Any], end: int) -> bool:
        return entry["due"] < end


class ClockStopsAtLastTimer(Model):
    """Leaves the clock at the last timer that fired, or where it was."""

    def finish(self, end: int) -> None:
        return None


class TimersSkipTheDouble(Model):
    """Fires a timer without calling the double through the usual path."""

    def fire(self, timer: dict[str, Any], due: int) -> None:
        self.clock = due


class TimersCallAtTheEnd(Model):
    """Makes every call of an advance at its end time."""

    def advance(self, ms: int) -> list[str]:
        self.end_of_advance = self.clock + ms
        return super().advance(ms)

    def fire(self, timer: dict[str, Any], due: int) -> None:
        self.clock = self.end_of_advance
        self.call(timer["name"], timer["method"], timer["args"])


class RepeatingTimerFiresOncePerAdvance(Model):
    """Fires a repeating timer at most once in one advance."""

    def advance(self, ms: int) -> list[str]:
        end = self.clock + ms
        fired = []
        seen: set[int] = set()
        while True:
            self.queue = [entry for entry in self.queue if entry["timer"]["live"]]
            ready = [
                entry
                for entry in self.queue
                if entry["due"] <= end and entry["timer"]["id"] not in seen
            ]
            if not ready:
                break
            entry = min(ready, key=self.firing_key)
            self.queue.remove(entry)
            timer = entry["timer"]
            seen.add(timer["id"])
            if timer["every"]:
                self.queue_up(timer, entry["due"] + timer["every"])
            else:
                timer["live"] = False
            fired.append(f"{timer['id']}@{entry['due']}")
            self.fire(timer, entry["due"])
        self.clock = end
        return fired


class FailedTimerTakesAnId(Model):
    """Uses up an id on a timer for a missing double."""

    def make_timer(self, delay: int, every: int, name: str, method: str, args: list[str]) -> int:
        if name not in self.doubles:
            self.timers.append({"id": len(self.timers) + 1, "live": False})
            return -1
        return super().make_timer(delay, every, name, method, args)


class CancelAfterFiring(Model):
    """Says a one-shot timer that already fired was cancelled."""

    def cancel(self, timer_id: int) -> bool:
        known = any(timer["id"] == timer_id for timer in self.timers)
        return super().cancel(timer_id) or known


class PendingByTimerId(Model):
    """Lists the waiting timers by id."""

    def pending(self) -> list[str]:
        live = [entry for entry in self.queue if entry["timer"]["live"]]
        ordered = sorted(live, key=lambda entry: entry["timer"]["id"])
        return [f"{entry['timer']['id']}@{entry['due']}" for entry in ordered]


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_kind_of_answer():
    answers = set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "call" and got.startswith("!"):
                answers.add(got)
            if op in ("verify", "verifyAll"):
                answers.update(line.split(" ")[0] for line in got)
    assert answers == {"!unknown", "!unexpected", "missing", "unexpected"}
