"""`python -m cs_runner --request R --out O` (docs/specs/runners.md#invocation).

Exit codes: 0 once `bye` is written, whatever the case outcomes; 2 for a request that cannot be
run; 3 after `restart_requested` (a stress run left worker threads alive); anything else is a
crash, which the CLI reports on the case in progress.
"""

import argparse
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from cs_runner.bench import run_bench_jobs
from cs_runner.concurrent import RestartRequestError, run_concurrent_job
from cs_runner.errors import BadRequestError
from cs_runner.events import EventWriter
from cs_runner.jobs import run_job
from cs_runner.request import BenchRequest, ConcurrentJob, TestRequest, parse_request

COMPLETED_EXIT_CODE = 0
BAD_REQUEST_EXIT_CODE = 2
RESTART_EXIT_CODE = 3
CASE_STACK_BYTES = 256 * 1024 * 1024
RECURSION_LIMIT = 10**6


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parse_arguments(argv)
    with Path(arguments.out).open("w", encoding="utf-8") as stream:
        events = EventWriter(stream)
        events.hello()
        try:
            request = parse_request(Path(arguments.request).read_text(encoding="utf-8"))
        except (BadRequestError, OSError, UnicodeDecodeError) as error:
            print(f"cs_runner: bad request: {error}", file=sys.stderr)
            return BAD_REQUEST_EXIT_CODE
        try:
            _run_with_deep_stack(lambda: _run(request, events))
        except RestartRequestError:
            return RESTART_EXIT_CODE
        events.bye()
    return COMPLETED_EXIT_CODE


def _run(request: TestRequest | BenchRequest, events: EventWriter) -> None:
    match request:
        case TestRequest(jobs):
            for job in jobs:
                if isinstance(job, ConcurrentJob):
                    run_concurrent_job(job, events)
                else:
                    run_job(job, events)
        case BenchRequest(jobs):
            run_bench_jobs(jobs, events)


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="cs_runner", description="coding-study Python runner")
    parser.add_argument("--request", required=True, help="request file (JSON)")
    parser.add_argument("--out", required=True, help="event file to write (JSON Lines)")
    return parser.parse_args(argv)


def _run_with_deep_stack(work: Callable[[], None]) -> None:
    """Runs `work` in a thread with a 256 MiB stack and a high recursion limit, so recursive
    solutions do not overflow; an exception from `work` is re-raised here."""
    failures: list[BaseException] = []

    def guarded() -> None:
        try:
            work()
        except BaseException as error:
            failures.append(error)

    previous_limit = sys.getrecursionlimit()
    previous_stack = threading.stack_size(CASE_STACK_BYTES)
    sys.setrecursionlimit(RECURSION_LIMIT)
    try:
        worker = threading.Thread(target=guarded, name="cs-runner-cases")
        worker.start()
        worker.join()
    finally:
        threading.stack_size(previous_stack)
        sys.setrecursionlimit(previous_limit)
    if failures:
        raise failures[0]
