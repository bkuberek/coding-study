"""Runs any language runner as a subprocess (docs/specs/runners.md).

Writes the request file, follows the JSON Lines event file, enforces the hang guard, and restarts
the runner after a hang or crash. Language adapters only supply the launch command through
`LanguageRunner.prepare`; nothing here is language-specific.

Watchdog phases, measured from the latest event:

- before `hello`: the launch's hello timeout; expiry is an environment error;
- during a call (test mode: between `case_start` and `case_result`; bench mode: after a
  `bench_start`): the case's hang guard, or the bench job's;
- anywhere else: `idle_limit_ms` (for example a module that hangs while loading).

A hang or crash is reported on the case (or bench target) in progress, or on the next one not
run yet when nothing is in progress, and the runner restarts with the work still pending.

After a stress run that left threads alive, a runner writes `restart_requested` and exits with
code 3 (docs/specs/runners.md#exit-codes-hang-guard-and-restarts-additions): it restarts for the
remaining cases without using up the crash-restart budget. Each stress run can ask once, so these
restarts are bounded by the stress runs in the request.

A launch with a debug agent (docs/specs/runners.md#debug-mode) waits for the IDE: no phase has a
limit, the runner is never restarted, and its standard output is kept, because the agent says there
when it listens. The session's ready line goes to `DebugLaunch.announce` once the agent listens, or
as the runner starts when it connects to an IDE that is already listening; that runner exits at once
while nobody listens, so it is launched again for a while. When a debug attempt ends, whatever it
leaves running from the launch's `scratch` directory is killed: a debug server that lets go of its
runner exits, and the runner (in a process group of its own) runs on.
"""

import json
import os
import signal
import subprocess
import tempfile
import time
from collections import deque
from contextlib import ExitStack
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from typing import IO, Protocol

from coding_study.adapters.bench_progress import BenchProgress
from coding_study.adapters.debug_process import (
    DebugOutput,
    kill_processes_started_from,
    terminated_like_interrupt,
)
from coding_study.adapters.runner_protocol import (
    Bye,
    CaseResult,
    CaseStart,
    Hello,
    JobEnd,
    JobStart,
    JsonObject,
    LoadError,
    ReportedOutcome,
    RestartRequested,
    RunnerEvent,
    accepted_hello,
    decode_event,
    encode_request,
)
from coding_study.application.ports import DebugLaunch, RunnerLaunch
from coding_study.domain.bench_runs import BenchReport, BenchRequest
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerProtocolError, RunnerStartError
from coding_study.domain.precedence import DEFAULT_HANG_GUARD_MS
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import (
    CaseOutcome,
    CaseReport,
    Crashed,
    JobReport,
    NotRun,
    Returned,
    RunCase,
    RunJob,
    RunnerInfo,
    RunReport,
    RunRequest,
    Stalled,
    StressCompleted,
    StressRun,
    TimedOut,
    UserError,
)

MAX_RESTARTS = 3
KEPT_RUNS = 20
STDERR_TAIL_LINES = 20
BAD_REQUEST_EXIT_CODE = 2
RESTART_EXIT_CODE = 3
STRESS_FEATURE = "stress"
POLL_INTERVAL_SECONDS = 0.005
EXIT_GRACE_SECONDS = 5.0
MILLISECONDS_PER_SECOND = 1000
CONNECT_PATIENCE_SECONDS = 10.0
"""How long a runner that connects to an IDE keeps trying while nobody listens."""
CONNECT_FIRST_DELAY_SECONDS = 0.2
CONNECT_MAX_DELAY_SECONDS = 1.0
DEBUG_NOT_RESTARTED = "the runner ended during the debug session; it is not restarted"


class SubprocessRunner:
    """`RunnerProcess` for every language; one directory per run under `runs_directory`.

    A launch's `scratch` directory is removed when its run ends, whether it completes, fails or is
    interrupted."""

    def __init__(
        self,
        runs_directory: Path,
        idle_limit_ms: int = DEFAULT_HANG_GUARD_MS,
        connect_patience_seconds: float = CONNECT_PATIENCE_SECONDS,
    ) -> None:
        self._runs_directory = runs_directory
        self._limits = _Limits(idle_limit_ms, connect_patience_seconds)

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        progress = _RunProgress(request)
        if not self._attempts(launch, progress):
            progress.mark_pending_not_run(_not_restarted_reason(launch))
        return progress.report()

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        progress = BenchProgress(request)
        if not self._attempts(launch, progress):
            progress.note(f"the runner was restarted {MAX_RESTARTS} times; the bench stopped early")
        return progress.report()

    def _attempts(self, launch: RunnerLaunch, progress: "_Progress") -> bool:
        """Runs and restarts the runner until the work is done; False when crash restarts ran
        out (a debug session allows none). Restarts the runner asked for do not count."""
        try:
            return self._attempt_until_done(launch, progress)
        finally:
            if launch.scratch is not None:
                rmtree(launch.scratch, ignore_errors=True)

    def _attempt_until_done(self, launch: RunnerLaunch, progress: "_Progress") -> bool:
        run_directory = self._new_run_directory()
        allowed_crashes = 0 if launch.debug else MAX_RESTARTS
        attempt = crashes = 0
        while True:
            files = _AttemptFiles(run_directory, attempt)
            _Attempt(launch, progress, files, self._limits).run()
            if progress.is_complete():
                return True
            attempt += 1
            crashes += 0 if progress.restart_requested else 1
            if crashes > allowed_crashes:
                return False

    def _new_run_directory(self) -> Path:
        self._runs_directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        directory = Path(tempfile.mkdtemp(prefix=f"{stamp}-", dir=self._runs_directory))
        self._remove_old_runs()
        return directory

    def _remove_old_runs(self) -> None:
        runs = sorted(path for path in self._runs_directory.iterdir() if path.is_dir())
        for old_run in runs[:-KEPT_RUNS]:
            rmtree(old_run, ignore_errors=True)


def _not_restarted_reason(launch: RunnerLaunch) -> str:
    if launch.debug is not None:
        return DEBUG_NOT_RESTARTED
    return f"the runner was restarted {MAX_RESTARTS} times"


@dataclass(frozen=True, slots=True)
class _Limits:
    idle_ms: int
    """The longest gap between events outside hello and a case; see the watchdog phases."""
    connect_seconds: float


class _Progress(Protocol):
    """The work of one run across restarts, and the protocol state of the current attempt."""

    @property
    def said_hello(self) -> bool: ...

    @property
    def call_limit_ms(self) -> int | None:
        """The hang guard of the call in progress; None when no call is in progress."""
        ...

    @property
    def restart_requested(self) -> bool:
        """The current attempt ended with `restart_requested` (exit code 3 expected)."""
        ...

    def begin_attempt(self) -> JsonObject:
        """The request for the work still pending; resets the per-attempt protocol state."""
        ...

    def apply(self, event: RunnerEvent) -> None: ...

    def interrupt(self, outcome: Crashed | TimedOut) -> None:
        """Record a hang or crash on the work in progress, else on the next pending work."""
        ...

    def is_complete(self) -> bool: ...


class _RunProgress:
    """Outcomes so far and the protocol state of the current attempt."""

    def __init__(self, request: RunRequest) -> None:
        self._request = request
        self._outcomes: dict[str, dict[str, CaseOutcome]] = {job.job_id: {} for job in request.jobs}
        self._load_errors: dict[str, UserError] = {}
        self._finished_jobs: set[str] = set()
        self._runner: RunnerInfo | None = None
        self._attempt_jobs: dict[str, RunJob] = {}
        self._said_hello = False
        self._current_job: str | None = None
        self._case_in_progress: tuple[str, RunCase] | None = None
        self._last_stress_result: tuple[str, str] | None = None
        self._restart_requested = False
        self._restarted_after: dict[str, list[str]] = {job.job_id: [] for job in request.jobs}
        self._needs_stress = any(job.kind is ProblemKind.CONCURRENT for job in request.jobs)

    @property
    def said_hello(self) -> bool:
        return self._said_hello

    @property
    def restart_requested(self) -> bool:
        return self._restart_requested

    @property
    def call_limit_ms(self) -> int | None:
        return self._case_in_progress[1].hang_guard_ms if self._case_in_progress else None

    def begin_attempt(self) -> JsonObject:
        """The jobs and cases still to run; resets the per-attempt protocol state."""
        pending = RunRequest(
            tuple(
                replace(job, cases=self._pending_cases(job))
                for job in self._request.jobs
                if job.job_id not in self._finished_jobs
            )
        )
        self._attempt_jobs = {job.job_id: job for job in pending.jobs}
        self._said_hello = False
        self._current_job = None
        self._case_in_progress = None
        self._last_stress_result = None
        self._restart_requested = False
        return encode_request(pending)

    def apply(self, event: RunnerEvent) -> None:
        if isinstance(event, Hello):
            self._hello(event)
            return
        if not self._said_hello:
            raise RunnerProtocolError(f"runner sent {type(event).__name__} before hello")
        if self._restart_requested:
            raise RunnerProtocolError(f"runner sent {type(event).__name__} after restart_requested")
        match event:
            case JobStart(job_id):
                self._job_start(job_id)
            case CaseStart(job_id, case_id):
                self._case_start(job_id, case_id)
            case CaseResult(job_id, case_id, outcome):
                self._case_result(job_id, case_id, outcome)
            case LoadError(job_id, error):
                self._load_error(job_id, error)
            case JobEnd(job_id):
                self._job_end(job_id)
            case RestartRequested():
                self._restart()
            case Bye():
                self._bye()
            case _:
                raise RunnerProtocolError(f"runner sent {type(event).__name__} in test mode")

    def interrupt(self, outcome: Crashed | TimedOut) -> None:
        """Record a hang or crash on the case in progress, else on the next pending case."""
        target = self._case_in_progress or self._next_pending_case()
        self._case_in_progress = None
        if target is not None:
            job_id, case = target
            self._outcomes[job_id][case.id] = outcome

    def is_complete(self) -> bool:
        return all(
            job.job_id in self._finished_jobs or not self._pending_cases(job)
            for job in self._request.jobs
        )

    def mark_pending_not_run(self, reason: str) -> None:
        for job in self._request.jobs:
            if job.job_id not in self._load_errors:
                for case in self._pending_cases(job):
                    self._outcomes[job.job_id][case.id] = NotRun(reason)

    def report(self) -> RunReport:
        if self._runner is None:
            raise RunnerProtocolError("runner never said hello")
        return RunReport(self._runner, tuple(self._job_report(job) for job in self._request.jobs))

    def _job_report(self, job: RunJob) -> JobReport:
        outcomes = self._outcomes[job.job_id]
        cases = tuple(
            CaseReport(case.id, outcomes[case.id]) for case in job.cases if case.id in outcomes
        )
        restarted_after = tuple(self._restarted_after[job.job_id])
        return JobReport(job.job_id, cases, self._load_errors.get(job.job_id), restarted_after)

    def _hello(self, hello: Hello) -> None:
        """A concurrent job needs a runner with the `stress` feature (runners.md#capability)."""
        accepted = accepted_hello(hello, self._said_hello)
        if self._needs_stress and STRESS_FEATURE not in accepted.features:
            raise RunnerStartError(f"runner {accepted.runner} does not support concurrent problems")
        self._runner = self._runner or accepted
        self._said_hello = True

    def _job_start(self, job_id: str) -> None:
        self._attempt_job(job_id)
        self._require_no_case_in_progress("job_start")
        self._current_job = job_id

    def _case_start(self, job_id: str, case_id: str) -> None:
        self._require_no_case_in_progress("case_start")
        if job_id != self._current_job:
            raise RunnerProtocolError(f'case_start for job "{job_id}" outside job_start')
        case = next((case for case in self._attempt_job(job_id).cases if case.id == case_id), None)
        if case is None or case_id in self._outcomes[job_id]:
            raise RunnerProtocolError(f'unexpected case "{case_id}" in job "{job_id}"')
        self._case_in_progress = (job_id, case)

    def _case_result(self, job_id: str, case_id: str, outcome: ReportedOutcome) -> None:
        in_progress = self._case_in_progress
        if in_progress is None or (in_progress[0], in_progress[1].id) != (job_id, case_id):
            raise RunnerProtocolError(f'case_result for "{job_id}/{case_id}" without case_start')
        problem = _result_problem(in_progress[1], outcome)
        if problem is not None:
            raise RunnerProtocolError(f'case_result for "{job_id}/{case_id}": {problem}')
        self._outcomes[job_id][case_id] = outcome
        self._case_in_progress = None
        is_stress = isinstance(in_progress[1].input, StressRun)
        self._last_stress_result = (job_id, case_id) if is_stress else None

    def _restart(self) -> None:
        """Only right after a stress run's result; the runner exits with code 3 next."""
        if self._last_stress_result is None:
            raise RunnerProtocolError("restart_requested without a stress run result before it")
        job_id, case_id = self._last_stress_result
        self._restarted_after[job_id].append(case_id)
        self._restart_requested = True

    def _load_error(self, job_id: str, error: UserError) -> None:
        self._attempt_job(job_id)
        self._require_no_case_in_progress("load_error")
        self._load_errors[job_id] = error
        self._finished_jobs.add(job_id)

    def _job_end(self, job_id: str) -> None:
        job = self._attempt_job(job_id)
        self._require_no_case_in_progress("job_end")
        if job_id not in self._load_errors and self._pending_cases(job):
            raise RunnerProtocolError(f'runner ended job "{job_id}" without running every case')
        self._finished_jobs.add(job_id)
        self._current_job = None

    def _bye(self) -> None:
        self._require_no_case_in_progress("bye")
        if not self.is_complete():
            raise RunnerProtocolError("runner said bye without running every requested case")

    def _attempt_job(self, job_id: str) -> RunJob:
        job = self._attempt_jobs.get(job_id)
        if job is None:
            raise RunnerProtocolError(f'unknown job "{job_id}"')
        return job

    def _require_no_case_in_progress(self, event: str) -> None:
        if self._case_in_progress is not None:
            raise RunnerProtocolError(f"runner sent {event} before the case_result of a case")

    def _pending_cases(self, job: RunJob) -> tuple[RunCase, ...]:
        outcomes = self._outcomes[job.job_id]
        return tuple(case for case in job.cases if case.id not in outcomes)

    def _next_pending_case(self) -> tuple[str, RunCase] | None:
        return next(
            (
                (job.job_id, case)
                for job in self._attempt_jobs.values()
                if job.job_id not in self._load_errors
                for case in self._pending_cases(job)
            ),
            None,
        )


class _AttemptFiles:
    def __init__(self, run_directory: Path, attempt: int) -> None:
        self.request = run_directory / f"request-{attempt}.json"
        self.events = run_directory / f"events-{attempt}.jsonl"
        self.stderr = run_directory / f"stderr-{attempt}.txt"
        self.stdout = run_directory / f"stdout-{attempt}.txt"
        """Kept for debug runs only: debug agents announce themselves there."""

    def stderr_tail(self) -> tuple[str, ...]:
        if not self.stderr.exists():
            return ()
        lines = self.stderr.read_text(encoding="utf-8", errors="replace").splitlines()
        return tuple(deque(lines, maxlen=STDERR_TAIL_LINES))


class _EventLines:
    """Complete lines appended to the event file since the previous read."""

    def __init__(self, stream: IO[bytes]) -> None:
        self._stream = stream
        self._partial = b""

    def read(self) -> list[str]:
        chunk = self._stream.read()
        if not chunk:
            return []
        *complete, self._partial = (self._partial + chunk).split(b"\n")
        return [line.decode("utf-8", errors="replace") for line in complete if line.strip()]


class _NoDebuggerListeningError(Exception):
    """A runner that connects to the IDE found nobody listening yet."""


class _Attempt:
    """One runner process, from launch until `bye`, exit, or watchdog expiry; a runner that
    connects to the IDE's debugger is launched again until the IDE listens."""

    def __init__(
        self,
        launch: RunnerLaunch,
        progress: _Progress,
        files: _AttemptFiles,
        limits: _Limits,
    ) -> None:
        self._launch = launch
        self._progress = progress
        self._files = files
        self._limits = limits
        self._last_event_at = time.monotonic()
        self._announced = False
        self._output: DebugOutput | None = None

    def run(self) -> None:
        debug = self._launch.debug
        if debug is None:
            self._run_once()
            return
        with terminated_like_interrupt():
            if debug.session.connect:
                self._run_until_connected(debug)
            else:
                self._run_once()

    def _run_until_connected(self, debug: DebugLaunch) -> None:
        deadline = time.monotonic() + self._limits.connect_seconds
        delay = CONNECT_FIRST_DELAY_SECONDS
        while True:
            try:
                self._run_once()
                return
            except _NoDebuggerListeningError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RunnerStartError(_no_debugger_message(debug.session)) from None
                time.sleep(min(delay, remaining))
                delay = min(delay * 2, CONNECT_MAX_DELAY_SECONDS)

    def _run_once(self) -> None:
        request = self._progress.begin_attempt()
        self._files.request.write_text(json.dumps(request), encoding="utf-8")
        self._files.events.write_bytes(b"")
        with ExitStack() as streams:
            stderr = streams.enter_context(self._files.stderr.open("wb"))
            events = streams.enter_context(self._files.events.open("rb"))
            stdout = self._open_stdout(streams)
            process = self._start(stdout, stderr)
            try:
                self._follow(process, _EventLines(events))
            finally:
                try:
                    _kill_group(process)
                finally:
                    if self._launch.debug is not None:
                        kill_processes_started_from(self._launch.scratch, EXIT_GRACE_SECONDS)

    def _open_stdout(self, streams: ExitStack) -> IO[bytes] | int:
        """Debug agents print their ready line to standard output or error: keep both. An agent
        that writes a ready file instead finds it empty."""
        debug = self._launch.debug
        if debug is None:
            self._output = None
            return subprocess.DEVNULL
        if debug.ready_file is not None:
            debug.ready_file.write_bytes(b"")
        self._output = DebugOutput(debug, self._files.stdout, self._files.stderr)
        return streams.enter_context(self._files.stdout.open("wb"))

    def _start(self, stdout: IO[bytes] | int, stderr: IO[bytes]) -> subprocess.Popen[bytes]:
        arguments = ["--request", str(self._files.request), "--out", str(self._files.events)]
        try:
            process = subprocess.Popen(
                [*self._launch.command, *arguments],
                cwd=self._launch.cwd,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
        except OSError as error:
            raise RunnerStartError(
                f"cannot start runner {self._launch.command[0]}: {error.strerror or error}"
            ) from error
        self._last_event_at = time.monotonic()
        self._announce_connecting()
        return process

    def _follow(self, process: subprocess.Popen[bytes], lines: _EventLines) -> None:
        while True:
            exit_code = process.poll()
            self._announce_when_listening()
            if self._consume(lines):
                self._require_agent_to_have_listened()
                _wait_for_exit(process)
                return
            if exit_code is not None:
                self._ended(exit_code)
                return
            if self._expired():
                _kill_group(process)
                self._timed_out()
                return
            time.sleep(POLL_INTERVAL_SECONDS)

    def _consume(self, lines: _EventLines) -> bool:
        """Apply new events; True once the runner said bye."""
        for line in lines.read():
            event = decode_event(line)
            self._progress.apply(event)
            self._last_event_at = time.monotonic()
            if isinstance(event, Bye):
                return True
        return False

    def _announce(self, debug: DebugLaunch) -> None:
        self._announced = True
        debug.announce(debug.session.ready_line)

    def _announce_connecting(self) -> None:
        debug = self._launch.debug
        if debug is not None and debug.session.connect and not self._announced:
            self._announce(debug)

    def _announce_when_listening(self) -> None:
        debug, output = self._launch.debug, self._output
        if debug is None or output is None or self._announced:
            return
        if output.agent_listens():
            self._announce(debug)

    def _require_agent_to_have_listened(self) -> None:
        """A runner that finished a debug run never listened (Node starts without its inspector
        when the port is taken): nobody could have debugged it. The output is read once more,
        because the marker and `bye` may both have landed since the poll's last check."""
        debug, output = self._launch.debug, self._output
        if debug is None or output is None or self._announced or output.agent_listens():
            return
        session = debug.session
        raise RunnerStartError(
            f"the {session.language} runner finished without a debug agent listening on "
            f"{session.address}",
            output.tail(),
        )

    def _current_limit_ms(self) -> int:
        if not self._progress.said_hello:
            return self._launch.hello_timeout_ms
        call_limit_ms = self._progress.call_limit_ms
        return call_limit_ms if call_limit_ms is not None else self._limits.idle_ms

    def _expired(self) -> bool:
        """Never while debugging: a runner paused at a breakpoint is not hung."""
        if self._launch.debug is not None:
            return False
        elapsed_ms = (time.monotonic() - self._last_event_at) * MILLISECONDS_PER_SECOND
        return elapsed_ms > self._current_limit_ms()

    def _ended(self, exit_code: int) -> None:
        if exit_code == RESTART_EXIT_CODE and self._progress.restart_requested:
            return
        output = self._output
        if output is not None and not self._progress.said_hello:
            raise self._debug_start_failure(output, exit_code)
        stderr_tail = self._files.stderr_tail()
        if exit_code == BAD_REQUEST_EXIT_CODE and self._progress.call_limit_ms is None:
            raise RunnerProtocolError(
                "\n".join(("runner rejected the request (exit code 2)", *stderr_tail))
            )
        if not self._progress.said_hello:
            raise RunnerStartError(f"runner exited with code {exit_code} before hello", stderr_tail)
        self._progress.interrupt(Crashed(exit_code, stderr_tail))

    def _debug_start_failure(self, output: DebugOutput, exit_code: int) -> Exception:
        """A debug runner that ended before `hello`: no IDE was listening yet (a connecting
        runner is launched again), or the agent failed to start, or the IDE ended the session."""
        if output.refused_connection():
            return _NoDebuggerListeningError()
        return RunnerStartError(
            f"the debug session ended before the run started (runner exit code {exit_code})",
            output.tail(),
        )

    def _timed_out(self) -> None:
        limit_ms = self._current_limit_ms()
        if not self._progress.said_hello:
            raise RunnerStartError(
                f"runner did not say hello within {limit_ms} ms", self._files.stderr_tail()
            )
        self._progress.interrupt(TimedOut(limit_ms))


def _no_debugger_message(session: DebugSession) -> str:
    return (
        f"no debugger listening on {session.address}; "
        "start the IDE's 'Debug JVM (listen)' configuration first"
    )


def _result_problem(case: RunCase, outcome: ReportedOutcome) -> str | None:
    """Why `outcome` cannot be the result of `case`, or None: stress runs report the outputs of
    every script op, and only stress runs complete as stress runs or stall."""
    run = case.input
    if not isinstance(run, StressRun):
        is_stress_outcome = isinstance(outcome, StressCompleted | Stalled)
        return "a stress run result for a case that is no stress run" if is_stress_outcome else None
    if not isinstance(outcome, StressCompleted):
        is_plain_result = isinstance(outcome, Returned)
        return "a stress run result needs its sections" if is_plain_result else None
    expected = (
        len(run.setup.ops),
        tuple(len(worker.ops) for worker in run.workers),
        len(run.final.ops) if run.final else 0,
    )
    reported = (
        len(outcome.setup),
        tuple(len(worker) for worker in outcome.workers),
        len(outcome.final),
    )
    return None if reported == expected else "outputs do not match the scripts' ops"


def _wait_for_exit(process: subprocess.Popen[bytes]) -> None:
    if not _exited_within_grace(process):
        _kill_group(process)


def _exited_within_grace(process: subprocess.Popen[bytes]) -> bool:
    try:
        process.wait(timeout=EXIT_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        return False
    return True


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    """Kill the runner and anything it started; only while it runs, so its group id is ours."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # The runner may exit after the check above. macOS then answers EPERM instead of ESRCH
        # while it is exiting but not yet reapable; only a runner that stays alive is a real error.
        if not _exited_within_grace(process):
            raise
    process.wait()
