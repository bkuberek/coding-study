"""loop-controller promises that its hidden cases catch the classic mistakes of a harness's brakes:
a cap asked in the wrong order or off by one, state that leaks from one run into the next, two
failures compared as text instead of as the same failure, a streak that is not reset or that
counts the wrong things, a budget tested with the wrong comparison or in the wrong order, a
claim of done that skips its check, and a trace that is not the trace of the last run. These tests
replay every case against a model of the controller written from the statement as two ordered
lists of questions, which must give every expected output, and against that model with one
mistake planted at a time, which some hidden case must fail. A mistake that crashes fails its case,
as a thrown exception does in the grader."""

import json
import re
from collections.abc import Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0323-loop-controller"
CASES: Sequence[dict[str, Any]] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))[
    "cases"
]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

BEFORE = ("max_iterations", "token_budget", "time_budget", "out_of_steps")
AFTER = ("final", "token_budget", "time_budget", "no_progress")


class Model:
    """The controller as the statement words it: facts about the state, asked in a fixed order
    before an iteration and after a step. Each mistake below overrides one hook."""

    before_order: tuple[str, ...] = BEFORE
    after_order: tuple[str, ...] = AFTER

    def __init__(self) -> None:
        self.limit = 0
        self.max_tokens = -1
        self.max_millis = -1
        self.check: dict[str, str] | None = None
        self.iterations_done = 0
        self.rows: list[list[str]] = []
        self.tripped_rows: list[list[str]] = []

    # --- hooks, one idea each
    def args_key(self, text: str) -> str:
        return json.dumps(json.loads(text), sort_keys=True)

    def message_key(self, text: str) -> str:
        return re.sub(r"\d+", "#", " ".join(text.split()))

    def signature(self, action: str, args: str, message: str) -> tuple[str, str, str]:
        return (action, self.args_key(args), self.message_key(message))

    def budget_spent(self, used: int, limit: int) -> bool:
        return limit != -1 and used >= limit

    def budget_exceeded(self, used: int, limit: int) -> bool:
        return limit != -1 and used > limit

    def verdict_for(self, claim: str) -> str:
        assert self.check is not None
        return self.check.get(claim, "no verdict")

    def accepts(self, verdict: str) -> bool:
        return verdict == "pass"

    def begin_run(self) -> None:
        self.iterations_done = 0
        self.rows = []
        self.tripped_rows = []

    def streak_after(self, streak: int, previous: Any, current: Any) -> int:
        if current is None:
            return 0
        return streak + 1 if current == previous else 1

    def reached(self, streak: int) -> bool:
        return self.limit > 0 and streak >= self.limit

    def remembered(self, previous: Any, current: Any) -> Any:
        return current

    def is_failure_outcome(self, outcome: str) -> bool:
        return outcome in ("error", "rejected")

    def stop_row(self, reason: str, tokens: int, millis: int) -> list[str]:
        return ["stop", reason, str(self.iterations_done), str(tokens), str(millis)]

    def step_row(self, n: int, action: str, outcome: str, tokens: int, millis: int) -> list[str]:
        return ["step", str(n), action, outcome, str(tokens), str(millis)]

    def feedback_goes_after_step(self) -> bool:
        return True

    # --- the questions
    def facts_before(
        self, cap: int, steps: Sequence[Sequence[str]], tokens: int, millis: int
    ) -> dict[str, bool]:
        return {
            "max_iterations": self.iterations_done >= cap,
            "token_budget": self.budget_spent(tokens, self.max_tokens),
            "time_budget": self.budget_spent(millis, self.max_millis),
            "out_of_steps": self.iterations_done >= len(steps),
        }

    def facts_after(self, accepted: bool, tokens: int, millis: int, streak: int) -> dict[str, bool]:
        return {
            "final": accepted,
            "token_budget": self.budget_exceeded(tokens, self.max_tokens),
            "time_budget": self.budget_exceeded(millis, self.max_millis),
            "no_progress": self.reached(streak),
        }

    def ask(
        self, order: Sequence[str], facts: dict[str, bool], phase: str, totals: tuple[int, int]
    ):
        reason = next((name for name in order if facts[name]), "")
        if reason in ("token_budget", "time_budget"):
            used = {"token_budget": totals[0], "time_budget": totals[1]}
            limit = {"token_budget": self.max_tokens, "time_budget": self.max_millis}
            self.tripped_rows = [
                [name, phase, str(self.iterations_done), str(used[name]), str(limit[name])]
                for name in ("token_budget", "time_budget")
                if facts[name]
            ]
        return reason

    def judge(self, action: str, status: str, result: str) -> tuple[str, str]:
        if action != "final":
            return status, ""
        if self.check is None:
            return "accepted", ""
        verdict = self.verdict_for(result)
        return ("accepted", "") if self.accepts(verdict) else ("rejected", verdict)

    # --- the methods
    def run(self, max_iterations: int, steps: list[list[str]]) -> str:
        self.begin_run()
        tokens = millis = streak = 0
        previous: Any = None
        while True:
            reason = self.ask(
                self.before_order,
                self.facts_before(max_iterations, steps, tokens, millis),
                "before",
                (tokens, millis),
            )
            if reason:
                break
            action, args, status, result, step_tokens, step_millis = steps[self.iterations_done]
            self.iterations_done += 1
            tokens += int(step_tokens)
            millis += int(step_millis)
            outcome, feedback = self.judge(action, status, result)
            row = self.step_row(self.iterations_done, action, outcome, tokens, millis)
            extra = [["feedback", str(self.iterations_done), feedback]] if feedback else []
            self.rows.extend([row, *extra] if self.feedback_goes_after_step() else [*extra, row])
            current = None
            if self.is_failure_outcome(outcome):
                message = feedback if outcome == "rejected" else result
                current = self.signature(action, args, message)
            streak = self.streak_after(streak, previous, current)
            previous = self.remembered(previous, current)
            reason = self.ask(
                self.after_order,
                self.facts_after(outcome == "accepted", tokens, millis, streak),
                "after",
                (tokens, millis),
            )
            if reason:
                break
        stop = self.stop_row(reason, tokens, millis)
        if stop:
            self.rows.append(stop)
        return reason

    def iterations(self) -> int:
        return self.iterations_done

    def set_no_progress_limit(self, limit: int) -> None:
        self.limit = limit

    def set_budgets(self, max_tokens: int, max_millis: int) -> None:
        self.max_tokens, self.max_millis = max_tokens, max_millis

    def tripped(self) -> list[list[str]]:
        return self.tripped_rows

    def set_check(self, claims: list[str], verdicts: list[str]) -> None:
        self.check = dict(zip(claims, verdicts, strict=True))

    def summary(self) -> list[list[str]]:
        return self.rows


# ---------------------------------------------------------------- level 1: the order and the state
class OutOfStepsBeforeTheCap(Model):
    """Asks whether the steps ran out before it asks about the cap."""

    before_order = ("out_of_steps", "max_iterations", "token_budget", "time_budget")


class CapAllowsOneMore(Model):
    """Lets one more iteration run than the cap."""

    def facts_before(self, cap, steps, tokens, millis):
        return super().facts_before(cap + 1, steps, tokens, millis)


class CapStopsOneEarly(Model):
    """Stops one iteration before the cap, which loses a final answer on the last one."""

    def facts_before(self, cap, steps, tokens, millis):
        return super().facts_before(max(cap - 1, 0), steps, tokens, millis)


class IterationsAccumulate(Model):
    """Keeps counting the iterations of earlier runs."""

    def begin_run(self) -> None:
        self.rows = []
        self.tripped_rows = []


class StepsAfterTheFinalKeepRunning(Model):
    """Does not stop at a final answer when there is no check."""

    def facts_after(self, accepted, tokens, millis, streak):
        return super().facts_after(False, tokens, millis, streak)


# ---------------------------------------------------------------- level 2: the same failure
class ArgsComparedAsText(Model):
    """Compares the arguments as written."""

    def args_key(self, text: str) -> str:
        return text


class ArgsWithoutWhiteSpaceOnly(Model):
    """Removes the white space of the arguments but keeps the order of the keys."""

    def args_key(self, text: str) -> str:
        return re.sub(r"\s", "", text)


class ArgsParsedLoosely(Model):
    """Compares parsed values with == so that true equals 1."""

    def signature(self, action, args, message):
        return (action, json.loads(args), self.message_key(message))


class ArrayOrderIgnored(Model):
    """Sorts the items of arrays, which makes [1, 2] and [2, 1] the same."""

    def args_key(self, text: str) -> str:
        def fix(value):
            if isinstance(value, list):
                return sorted((fix(item) for item in value), key=repr)
            if isinstance(value, dict):
                return {key: fix(item) for key, item in value.items()}
            return value

        return json.dumps(fix(json.loads(text)), sort_keys=True)


class ArgsIgnored(Model):
    """Compares the action and the message only."""

    def args_key(self, text: str) -> str:
        return ""


class ActionIgnored(Model):
    """Compares the arguments and the message only."""

    def signature(self, action, args, message):
        return ("", self.args_key(args), self.message_key(message))


class DigitsNotMasked(Model):
    """Keeps the digits of the message."""

    def message_key(self, text: str) -> str:
        return " ".join(text.split())


class WhiteSpaceNotCollapsed(Model):
    """Trims the message but keeps runs of white space."""

    def message_key(self, text: str) -> str:
        return re.sub(r"\d+", "#", text.strip())


class MessageCaseFolded(Model):
    """Lower-cases the message."""

    def message_key(self, text: str) -> str:
        return super().message_key(text).lower()


class EveryDigitMasked(Model):
    """Replaces each digit with a `#`, so that 12 and 3 are different."""

    def message_key(self, text: str) -> str:
        return re.sub(r"\d", "#", " ".join(text.split()))


class StreakKeptThroughSuccess(Model):
    """Does not end the streak when a step is not a failure."""

    def streak_after(self, streak, previous, current):
        if current is None:
            return streak
        return super().streak_after(streak, previous, current)

    def remembered(self, previous, current):
        return previous if current is None else current


class StreakCountsAllTheSameFailures(Model):
    """Counts the same failure over the whole run, not only in a row."""

    def begin_run(self) -> None:
        super().begin_run()
        self.seen: dict[Any, int] = {}

    def streak_after(self, streak, previous, current):
        if current is None:
            return streak
        self.seen[current] = self.seen.get(current, 0) + 1
        return self.seen[current]


class StreakOffByOne(Model):
    """Needs one failure more than the limit."""

    def reached(self, streak: int) -> bool:
        return self.limit > 0 and streak > self.limit


class StreakStopsOneEarly(Model):
    """Stops when the streak is one short of the limit."""

    def reached(self, streak: int) -> bool:
        return self.limit > 0 and streak >= self.limit - 1


class ZeroLimitStopsAtOnce(Model):
    """Reads a limit of 0 as 'stop at the first failure'."""

    def reached(self, streak: int) -> bool:
        return streak >= max(self.limit, 1)


class SuccessesCountAsFailures(Model):
    """Treats the same successful call repeated as the same failure."""

    def is_failure_outcome(self, outcome: str) -> bool:
        return True


class CapBeforeNoProgress(Model):
    """Asks the cap right after a step, before the no-progress question."""

    def facts_after(self, accepted, tokens, millis, streak):
        facts = super().facts_after(accepted, tokens, millis, streak)
        facts["no_progress"] = facts["no_progress"] and self.iterations_done < self.cap
        return facts

    def run(self, max_iterations, steps):
        self.cap = max_iterations
        return super().run(max_iterations, steps)


# ---------------------------------------------------------------- level 3: the budgets
class SpentUsesGreaterThan(Model):
    """Reads 'spent' as strictly above the limit, so a run can use exactly its budget and go on."""

    def budget_spent(self, used: int, limit: int) -> bool:
        return limit != -1 and used > limit


class ExceededUsesGreaterOrEqual(Model):
    """Reads 'exceeded' as at or above the limit."""

    def budget_exceeded(self, used: int, limit: int) -> bool:
        return limit != -1 and used >= limit


class ZeroBudgetIsNoLimit(Model):
    """Treats a limit of 0 like -1."""

    def budget_spent(self, used: int, limit: int) -> bool:
        return limit > 0 and used >= limit

    def budget_exceeded(self, used: int, limit: int) -> bool:
        return limit > 0 and used > limit


class NoCheckBeforeAStep(Model):
    """Looks at the budgets only after a step."""

    def budget_spent(self, used: int, limit: int) -> bool:
        return False


class NoCheckAfterAStep(Model):
    """Looks at the budgets only before a step."""

    def budget_exceeded(self, used: int, limit: int) -> bool:
        return False


class BudgetsBeforeTheCap(Model):
    """Asks the budgets before the cap."""

    before_order = ("token_budget", "time_budget", "max_iterations", "out_of_steps")


class StepsOutBeforeTheBudgets(Model):
    """Asks whether the steps ran out before the budgets."""

    before_order = ("max_iterations", "out_of_steps", "token_budget", "time_budget")


class TimeBeforeTokens(Model):
    """Reports the time budget first when both trip."""

    before_order = ("max_iterations", "time_budget", "token_budget", "out_of_steps")
    after_order = ("final", "time_budget", "token_budget", "no_progress")


class FinalLosesToTheBudget(Model):
    """Reports a budget that a final answer went over instead of the answer."""

    after_order = ("token_budget", "time_budget", "final", "no_progress")


class NoProgressBeforeTheBudgets(Model):
    """Asks no_progress before the budgets after a step."""

    after_order = ("final", "no_progress", "token_budget", "time_budget")


class FinalAfterNoProgress(Model):
    """Asks no_progress before final."""

    after_order = ("no_progress", "final", "token_budget", "time_budget")


class TrippedListsOnlyTheFirst(Model):
    """Lists only the budget that is reported."""

    def ask(self, order, facts, phase, totals):
        reason = super().ask(order, facts, phase, totals)
        self.tripped_rows = self.tripped_rows[:1]
        return reason


class TrippedKeepsAnOldRun(Model):
    """Does not clear the tripped rows when a run starts."""

    def begin_run(self) -> None:
        self.iterations_done = 0
        self.rows = []


class TrippedPhaseSwapped(Model):
    """Names the phase the other way round."""

    def ask(self, order, facts, phase, totals):
        return super().ask(order, facts, "after" if phase == "before" else "before", totals)


class TrippedListsNoSecondBudget(Model):
    """Reports a budget row only when it is the reason, never for a second budget."""

    def ask(self, order, facts, phase, totals):
        reason = super().ask(order, facts, phase, totals)
        self.tripped_rows = [row for row in self.tripped_rows if row[0] == reason]
        return reason


# ---------------------------------------------------------------- level 4: the claim and the trace
class CheckIgnored(Model):
    """Accepts every final answer even when a check is installed."""

    def judge(self, action, status, result):
        return ("accepted", "") if action == "final" else (status, "")


class VerdictCaseInsensitive(Model):
    """Accepts PASS as well as pass."""

    def accepts(self, verdict: str) -> bool:
        return verdict.lower() == "pass"


class VerdictTrimmed(Model):
    """Accepts 'pass ' as well as 'pass'."""

    def accepts(self, verdict: str) -> bool:
        return verdict.strip() == "pass"


class ClaimTrimmed(Model):
    """Looks a claim up after trimming white space."""

    def verdict_for(self, claim: str) -> str:
        assert self.check is not None
        return self.check.get(claim.strip(), "no verdict")


class UnknownClaimAccepted(Model):
    """Accepts a claim that no row names."""

    def verdict_for(self, claim: str) -> str:
        assert self.check is not None
        return self.check.get(claim, "pass")


class UnknownClaimHasAnotherFeedback(Model):
    """Gives another feedback text to a claim that no row names."""

    def verdict_for(self, claim: str) -> str:
        assert self.check is not None
        return self.check.get(claim, "fail")


class RejectionEndsTheRun(Model):
    """Stops the run at the first rejected claim."""

    def facts_after(self, accepted, tokens, millis, streak):
        facts = super().facts_after(accepted, tokens, millis, streak)
        facts["final"] = True
        return facts


class RejectionIsNotAFailure(Model):
    """Leaves a rejected claim out of the no-progress streak."""

    def is_failure_outcome(self, outcome: str) -> bool:
        return outcome == "error"


class RejectionComparedByClaim(Model):
    """Compares rejected claims by the answer text instead of the feedback."""

    def signature(self, action, args, message):
        if action == "final":
            return (action, self.args_key(args), "claim")
        return super().signature(action, args, message)


class FeedbackBeforeTheStepRow(Model):
    """Writes the feedback row before the step row."""

    def feedback_goes_after_step(self) -> bool:
        return False


class TotalsPerStepNotRunning(Model):
    """Writes the cost of the step in the step row instead of the running total."""

    def run(self, max_iterations, steps):
        reason = super().run(max_iterations, steps)
        previous = (0, 0)
        for row in self.rows:
            if row[0] == "step":
                now = (int(row[4]), int(row[5]))
                row[4], row[5] = str(now[0] - previous[0]), str(now[1] - previous[1])
                previous = now
        return reason


class NoStopRowWhenNothingRan(Model):
    """Leaves out the closing row of a run that executed nothing."""

    def stop_row(self, reason, tokens, millis):
        return [] if self.iterations_done == 0 else super().stop_row(reason, tokens, millis)


class SummaryAccumulates(Model):
    """Keeps the rows of earlier runs."""

    def begin_run(self) -> None:
        self.iterations_done = 0
        self.tripped_rows = []


class OutcomeOfAClaimIsOk(Model):
    """Names an accepted claim `ok` and a rejected one `error`."""

    def step_row(self, n, action, outcome, tokens, millis):
        outcome = {"accepted": "ok", "rejected": "error"}.get(outcome, outcome)
        return super().step_row(n, action, outcome, tokens, millis)


class LaterCheckAddsToTheEarlierOne(Model):
    """Merges a new check into the old one instead of replacing it."""

    def set_check(self, claims, verdicts):
        self.check = {**(self.check or {}), **dict(zip(claims, verdicts, strict=True))}


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: dict[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: dict[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, AssertionError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_reason_and_both_phases():
    reasons, phases, outcomes = set(), set(), set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "run":
                reasons.add(got)
            elif op == "tripped":
                phases.update(row[1] for row in got)
            elif op == "summary":
                outcomes.update(row[3] for row in got if row[0] == "step")
    assert reasons == {
        "final",
        "max_iterations",
        "out_of_steps",
        "no_progress",
        "token_budget",
        "time_budget",
    }
    assert phases == {"before", "after"}
    assert outcomes == {"ok", "error", "accepted", "rejected"}
