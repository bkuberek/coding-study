"""Suite jobs: a project's own tests, run by its framework inside the runner
(docs/specs/runners.md#suite-job).

Only a suite job imports the framework, so other jobs neither pay for importing pytest nor need it
installed.
"""

from cs_runner.events import EventWriter
from cs_runner.failures import UserError
from cs_runner.request import SuiteJob


def run_suite_job(job: SuiteJob, events: EventWriter) -> None:
    events.job_start(job.job_id)
    try:
        from cs_runner.pytest_suite import run_pytest
    except ImportError as error:
        message = f"pytest cannot be imported by the runner's interpreter: {error}"
        events.load_error(job.job_id, UserError(type(error).__name__, message))
    else:
        run_pytest(job, events)
    events.job_end(job.job_id)
