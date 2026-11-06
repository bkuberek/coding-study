"""`cstudy abort`: stop working on a problem (docs/specs/cli.md#cstudy-abort).

The attempt ends as `abandoned`, the status a `--fresh` start gives the attempt it replaces. Its
files stay where they are, and nothing else changes: no grade, no rating, no change to the review
schedule or to the progress of the problem. The attempt's timer stops with its end time.
"""

from coding_study.application.environment import Environment
from coding_study.application.ports import RunActivity
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import WorkspaceBusyError


def abort_attempt(environment: Environment, attempt: Attempt, activity: RunActivity) -> Attempt:
    """The attempt as it ends. Raises WorkspaceBusyError, having changed nothing, while a run or a
    job is active."""
    busy = activity.active_run()
    if busy is not None:
        raise WorkspaceBusyError(f"cstudy abort waits until it ends: {busy}")
    ended = attempt.abandoned(environment.clock.now())
    environment.progress.update_attempt(ended)
    return ended
