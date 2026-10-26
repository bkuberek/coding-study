"""A scriptable stand-in for a runner with the `stress` feature, for SubprocessRunner tests.

Each stress run's setup argument says what the run does (docs/specs/runners.md#concurrent-jobs):

    "ok"        every worker finishes; outputs are null, sections empty
    "error"     worker 1 throws at its op 0
    "stall"     the deadline passes with worker 0 inside op 0
    "restart"   "ok", then restart_requested and exit code 3
    "exit-3"    "ok", then exit code 3 without restart_requested
    "mismatch"  "ok" with one output missing from worker 0

Sequential cases of a concurrent job return their ops' count. `--startup no-stress` says hello
without features.
"""

import argparse
import json
import sys
from pathlib import Path

RESTART_EXIT_CODE = 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--startup", default="normal")
    arguments = parser.parse_args()
    with Path(arguments.out).open("w", encoding="utf-8") as out:

        def emit(**event):
            out.write(json.dumps(event) + "\n")
            out.flush()

        features = [] if arguments.startup == "no-stress" else ["stress"]
        emit(event="hello", runner="fake", protocol=1, runtime="0.1", features=features)
        request = json.loads(Path(arguments.request).read_text(encoding="utf-8"))
        for job in request["jobs"]:
            emit(event="job_start", job_id=job["job_id"])
            for case in job["cases"]:
                if run_case(emit, job["job_id"], case) is not None:
                    return RESTART_EXIT_CODE
            emit(event="job_end", job_id=job["job_id"])
        emit(event="bye")
    return 0


def run_case(emit, job_id, case):
    """Returns an exit code when the runner must stop after this case."""
    ids = {"job_id": job_id, "case_id": case["id"]}
    emit(event="case_start", **ids)
    stress = case.get("stress")
    if stress is None:
        emit(event="case_result", status="ok", output=len(case["ops"]), duration_ns=1000, **ids)
        return None
    action = stress["setup"]["args"][0][0]
    workers = [[None] * len(worker["ops"]) for worker in stress["workers"]]
    if action == "error":
        progress = [{"worker": 0, "completed": 1, "in_op": True}]
        error = {"type": "IndexError", "message": "empty"}
        emit(
            event="case_result",
            status="error",
            phase="worker",
            worker=1,
            op_index=0,
            error=error,
            progress=progress,
            duration_ns=500,
            **ids,
        )
        return None
    if action == "stall":
        progress = [{"worker": 0, "completed": 0, "in_op": True}]
        emit(event="case_result", status="stalled", progress=progress, duration_ns=7, **ids)
        return None
    if action == "mismatch":
        workers[0] = workers[0][:-1]
    final = [None] * len(stress["final"]["ops"]) if "final" in stress else []
    output = {"setup": [None], "workers": workers, "final": final}
    emit(event="case_result", status="ok", output=output, sections={}, duration_ns=9, **ids)
    if action == "restart":
        emit(event="restart_requested", reason="1 worker thread still alive")
        return RESTART_EXIT_CODE
    if action == "exit-3":
        return RESTART_EXIT_CODE
    return None


if __name__ == "__main__":
    sys.exit(main())
