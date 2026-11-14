import json
import re
from dataclasses import dataclass, field

FINAL = "final"
ERROR = "error"
ACCEPTED = "accepted"
REJECTED = "rejected"
PASS = "pass"
NO_VERDICT = "no verdict"
NO_LIMIT = -1


@dataclass(slots=True)
class _Run:
    """What the last run did: the counters the loop keeps and the reports it builds."""

    iterations: int = 0
    tokens: int = 0
    millis: int = 0
    reason: str = ""
    tripped: list[list[str]] = field(default_factory=list)
    summary: list[list[str]] = field(default_factory=list)


def _canonical_args(args: str) -> str:
    """The arguments as compact JSON with the keys of every object sorted."""
    return json.dumps(json.loads(args), sort_keys=True, separators=(",", ":"))


def _canonical_error(text: str) -> str:
    """Trim, collapse white space to one space, and replace each run of digits with `#`."""
    return re.sub(r"[0-9]+", "#", " ".join(text.split()))


class LoopController:
    def __init__(self) -> None:
        self._no_progress_limit = 0
        self._max_tokens = NO_LIMIT
        self._max_millis = NO_LIMIT
        self._verdicts: dict[str, str] | None = None
        self._last = _Run()

    # Level 1
    def run(self, max_iterations: int, steps: list[list[str]]) -> str:
        state = _Run()
        self._last = state
        streak_signature: tuple[str, str, str] | None = None
        streak = 0
        while not state.reason:
            state.reason = self._stop_before(state, max_iterations, len(steps))
            if state.reason:
                break
            action, args, status, result, tokens, millis = steps[state.iterations]
            state.iterations += 1
            state.tokens += int(tokens)
            state.millis += int(millis)
            outcome, feedback = self._judge(action, status, result)
            state.summary.append(
                ["step", str(state.iterations), action, outcome, str(state.tokens), str(state.millis)]
            )
            if feedback:
                state.summary.append(["feedback", str(state.iterations), feedback])
            if outcome == ACCEPTED:
                state.reason = FINAL
                break
            signature = None
            if outcome in (ERROR, REJECTED):
                text = feedback if outcome == REJECTED else result
                signature = (action, _canonical_args(args), _canonical_error(text))
            if signature is None:
                streak = 0
            elif signature == streak_signature:
                streak += 1
            else:
                streak = 1
            streak_signature = signature
            state.reason = self._stop_after(state, streak)
        state.summary.append(
            ["stop", state.reason, str(state.iterations), str(state.tokens), str(state.millis)]
        )
        return state.reason

    def iterations(self) -> int:
        return self._last.iterations

    # Level 2
    def set_no_progress_limit(self, limit: int) -> None:
        self._no_progress_limit = limit

    # Level 3
    def set_budgets(self, max_tokens: int, max_millis: int) -> None:
        self._max_tokens = max_tokens
        self._max_millis = max_millis

    def tripped(self) -> list[list[str]]:
        return self._last.tripped

    # Level 4
    def set_check(self, claims: list[str], verdicts: list[str]) -> None:
        self._verdicts = dict(zip(claims, verdicts, strict=True))

    def summary(self) -> list[list[str]]:
        return self._last.summary

    def _judge(self, action: str, status: str, result: str) -> tuple[str, str]:
        """The outcome of a step and the feedback it produces."""
        if action != FINAL:
            return status, ""
        if self._verdicts is None:
            return ACCEPTED, ""
        verdict = self._verdicts.get(result, NO_VERDICT)
        if verdict == PASS:
            return ACCEPTED, ""
        return REJECTED, verdict

    def _stop_before(self, state: _Run, max_iterations: int, available: int) -> str:
        if state.iterations >= max_iterations:
            return "max_iterations"
        reason = self._trip_budgets(state, "before")
        if reason:
            return reason
        return "out_of_steps" if state.iterations >= available else ""

    def _stop_after(self, state: _Run, streak: int) -> str:
        reason = self._trip_budgets(state, "after")
        if reason:
            return reason
        limit = self._no_progress_limit
        return "no_progress" if limit > 0 and streak >= limit else ""

    def _trip_budgets(self, state: _Run, phase: str) -> str:
        """Records the budgets that trip at this check and returns the first one's name.

        A budget is spent (`>=`) when a step is about to start and exceeded (`>`) after a step.
        """
        for reason, used, limit in (
            ("token_budget", state.tokens, self._max_tokens),
            ("time_budget", state.millis, self._max_millis),
        ):
            if limit == NO_LIMIT:
                continue
            if used >= limit if phase == "before" else used > limit:
                state.tripped.append([reason, phase, str(state.iterations), str(used), str(limit)])
        return state.tripped[0][0] if state.tripped else ""
