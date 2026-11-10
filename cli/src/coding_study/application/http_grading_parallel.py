"""Sending a parallel case: its `before` requests in order, then its burst all at once, then its
`after` request (docs/specs/service-projects.md#parallel-cases).

All of it shares the case's limit. The `after` request goes out even when the statuses are wrong,
since the state a race left is what explains them.
"""

from dataclasses import dataclass

from coding_study.application.http_grading_steps import StepRunner, StepsStopped
from coding_study.domain.http_case import HttpCaseInput, ParallelBurst
from coding_study.domain.http_grading import ExchangeFailed
from coding_study.domain.http_parallel import BurstAnswer, statuses_failures


@dataclass(frozen=True, slots=True)
class BurstAnswered:
    """Every request of the burst was answered; what was wrong with the answers, if anything, is
    judged together with the case's logs."""

    answer: BurstAnswer
    failures: tuple[str, ...]


type BurstEnd = BurstAnswered | StepsStopped | ExchangeFailed


def run_burst(runner: StepRunner, http: HttpCaseInput, burst: ParallelBurst) -> BurstEnd:
    """A request of the burst that brought back no answer ends the case, as the first one in the
    order the requests were written; a `before` request that went wrong ends it before the
    burst."""
    stopped = _before(runner, http)
    if stopped is not None:
        return stopped
    sent = runner.send_together(burst.requests)
    statuses: list[int] = []
    for answer in sent:
        if isinstance(answer, ExchangeFailed):
            return answer
        statuses.append(answer.status)
    failures = statuses_failures(burst.statuses, statuses)
    if burst.after is None:
        return BurstAnswered(BurstAnswer(tuple(statuses), None, runner.spent_ns), failures)
    after = runner.run((burst.after,))
    if isinstance(after, ExchangeFailed | StepsStopped):
        return after
    answer = BurstAnswer(tuple(statuses), after.answer, runner.spent_ns)
    return BurstAnswered(answer, (*failures, *after.failures))


def _before(runner: StepRunner, http: HttpCaseInput) -> StepsStopped | ExchangeFailed | None:
    steps = http.before_steps()
    if not steps:
        return None
    ended = runner.run(steps)
    if isinstance(ended, StepsStopped | ExchangeFailed):
        return ended
    return StepsStopped(ended.answer, ended.failures) if ended.failures else None
