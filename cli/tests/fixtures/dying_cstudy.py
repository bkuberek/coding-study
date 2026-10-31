"""Stands in for a `cstudy` that dies by SIGKILL while a run is going, for the tests of the orphan
guard (docs/specs/runners.md#process-lifecycle).

    dying_cstudy.py guard <scratch>   an OrphanGuard of <scratch> watches a group of two processes,
                                      a leader and a member; a third process runs from <scratch> in
                                      a group of its own, as a debug server's runner does. Prints
                                      `going` and the three process ids
    dying_cstudy.py runner <runs>     SubprocessRunner runs tests/fixtures/fake_runner.py on a case
                                      that hangs, with no hang guard in sight. Prints `going` once
                                      the case started
    dying_cstudy.py libtest <marker>  SubprocessTests runs a test process that creates <marker>,
                                      then sleeps

None of them ends by itself.
"""

import subprocess
import sys
import time
from pathlib import Path

from coding_study.adapters import process_liveness
from coding_study.adapters.languages.rust.project_suite import SubprocessTests
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.cases import FunctionInput
from coding_study.domain.naming import FunctionNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import CaseReport, FileTarget, RunCase, RunJob, RunRequest
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType

FAKE_RUNNER = Path(__file__).resolve().parent / "fake_runner.py"
FOREVER_SECONDS = 3600
HANG_GUARD_MS = FOREVER_SECONDS * 1000
SLEEP = f"import time; time.sleep({FOREVER_SECONDS})"
TOUCH_AND_SLEEP = f"import sys, time; open(sys.argv[1], 'w').close(); time.sleep({FOREVER_SECONDS})"
SIGNATURE = FunctionSignature(
    "step", (Param("step", ScalarType(Scalar.STRING)),), Returns(ScalarType(Scalar.INT))
)


def say(*words: object) -> None:
    print(*words, flush=True)


def guard(scratch: Path) -> "process_liveness.OrphanGuard":
    """The guard, which must stay referenced: one collected as garbage closes its pipe.

    A process joins only a group of its own session, so the leader starts a group in this one.
    None of them keeps this process's standard output, which the test reads to its end."""
    binary = scratch / "cs-runner"
    binary.symlink_to(sys.executable)
    orphan_guard = process_liveness.OrphanGuard(scratch)
    sleep = [sys.executable, "-c", SLEEP]
    leader = subprocess.Popen(sleep, stdout=subprocess.DEVNULL, process_group=0)
    member = subprocess.Popen(sleep, stdout=subprocess.DEVNULL, process_group=leader.pid)
    orphan_guard.watch(leader.pid)
    from_scratch = subprocess.Popen(
        [str(binary), "-c", SLEEP], stdout=subprocess.DEVNULL, start_new_session=True
    )
    say("going", leader.pid, member.pid, from_scratch.pid)
    return orphan_guard


class SayWhenCaseStarts:
    def case_started(self, job_id: str, case_id: str) -> None:
        say("going")

    def case_finished(self, job_id: str, report: CaseReport) -> None:
        pass


def runner(runs: Path) -> None:
    launch = RunnerLaunch((sys.executable, str(FAKE_RUNNER)), FAKE_RUNNER.parent, 5_000)
    step = FunctionInput({"step": {"do": "hang"}})
    names = FunctionNames("step", {"step": "step"})
    case = RunCase("hangs", step, HANG_GUARD_MS)
    job = RunJob("j", ProblemKind.FUNCTION, FileTarget("/w/s.py"), names, SIGNATURE, (case,))
    SubprocessRunner(runs).run(launch, RunRequest((job,)), SayWhenCaseStarts())


def libtest(marker: Path) -> None:
    command = (sys.executable, "-c", TOUCH_AND_SLEEP, str(marker))
    SubprocessTests().run(command, marker.parent, HANG_GUARD_MS)


def main() -> None:
    scenario, path = sys.argv[1], Path(sys.argv[2])
    if scenario == "guard":
        kept = guard(path)
        time.sleep(FOREVER_SECONDS)
        kept.release()
    elif scenario == "runner":
        runner(path)
    else:
        libtest(path)


if __name__ == "__main__":
    main()
