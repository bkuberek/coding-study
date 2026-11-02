"""A scriptable stand-in for a runner with the `clock` feature, for SubprocessRunner tests.

Each case's id says what the case does (docs/specs/runners.md#virtual-clock-and-stress-in-project-
jobs):

    "deadlock..."   stalled at its last operation, then restart_requested and exit code 3
    "stalled..."    stalled at its last operation, and the next case runs in the same process
    "fails..."      an error at its last operation, then restart_requested and exit code 3
    "restarts..."   ok, then restart_requested and exit code 3
    anything else   ok, one null output per operation

`--startup no-clock` says hello without the `clock` feature.
"""

import argparse
import json
import sys
from pathlib import Path

RESTART_EXIT_CODE = 3
REASON = "op {index} (@join r1): deadlock at 2000 ms"


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

        features = ["project"] if arguments.startup == "no-clock" else ["project", "clock"]
        emit(event="hello", runner="fake", protocol=1, runtime="0.1", features=features)
        request = json.loads(Path(arguments.request).read_text(encoding="utf-8"))
        for job in request["jobs"]:
            emit(event="job_start", job_id=job["job_id"])
            for case in job["cases"]:
                if run_case(emit, job["job_id"], case):
                    return RESTART_EXIT_CODE
            emit(event="job_end", job_id=job["job_id"])
        emit(event="bye")
    return 0


def run_case(emit, job_id, case) -> bool:
    """Whether the runner asked for a restart after the case."""
    ids = {"job_id": job_id, "case_id": case["id"]}
    emit(event="case_start", **ids)
    last = len(case["ops"]) - 1
    partial = [None] * last
    if case["id"].startswith(("deadlock", "stalled")):
        reason = REASON.format(index=last)
        stall = {"op_index": last, "reason": reason, "partial_output": partial}
        emit(event="case_result", status="stalled", **stall, duration_ns=7, **ids)
    elif case["id"].startswith("fails"):
        error = {"type": "panic", "message": "closed"}
        failure = {"op_index": last, "partial_output": partial}
        emit(event="case_result", status="error", error=error, **failure, duration_ns=7, **ids)
    else:
        output = [None] * len(case["ops"])
        emit(event="case_result", status="ok", output=output, duration_ns=9, **ids)
    if case["id"].startswith(("deadlock", "fails", "restarts")):
        emit(event="restart_requested", reason=f"goroutines of {case['id']} are still blocked")
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
