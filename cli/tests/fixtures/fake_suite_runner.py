"""A scriptable stand-in for a runner that hosts a project's test suite
(docs/specs/runners.md#suite-job), for SubprocessRunner tests.

The suite job's `root` holds `suite.json`, the tests the "framework" discovers, in order, each
with what it does:

    {"id": T, "do": "pass"}             case_result ok, without an output
    {"id": T, "do": "fail"}             case_result failed with message "assert 1 == 2"
    {"id": T, "do": "raise"}            case_result error
    {"id": T, "do": "skip"}             case_result skipped with message "later"
    {"id": T, "do": "hang"}             sleeps after case_start
    {"id": T, "do": "sleep", "seconds": S}
                                        sleeps S seconds after case_start, then case_result ok
    {"id": T, "do": "stall"}            sleeps before case_start
    {"id": T, "do": "crash"}            writes "crashed" to stderr and exits 9 after case_start
    {"id": T, "do": "environment", "variable": V}
                                        case_result ok, printing the variable's value
    {"id": T, "do": "output"}           case_result ok with an output, as only a case has
    {"id": T, "do": "repeat"}           case_start for this test, even when `skip` names it

Tests that `skip` names are left out, except "repeat". `--startup no-suite` says hello without the
`suite` feature, `--startup load-error` reports the job's load_error, and `--startup early-end`
ends the job while a test is in progress.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

FOREVER_SECONDS = 3600
CRASH_EXIT_CODE = 9


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--startup", default="normal")
    arguments = parser.parse_args()
    with Path(arguments.out).open("w", encoding="utf-8") as out:
        return Runner(out, arguments.startup).run(arguments.request)


class Runner:
    def __init__(self, out, startup):
        self.out = out
        self.startup = startup

    def emit(self, **event):
        self.out.write(json.dumps(event) + "\n")
        self.out.flush()

    def run(self, request_path):
        features = ["stress"] if self.startup == "no-suite" else ["stress", "project", "suite"]
        self.emit(event="hello", runner="fake", protocol=1, runtime="0.1", features=features)
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        for job in request["jobs"]:
            self.run_job(job)
        self.emit(event="bye")
        return 0

    def run_job(self, job):
        job_id = job["job_id"]
        self.emit(event="job_start", job_id=job_id)
        if self.startup == "load-error":
            error = {"type": "UsageError", "message": "unrecognized arguments"}
            self.emit(event="load_error", job_id=job_id, error=error)
        else:
            suite = json.loads((Path(job["root"]) / "suite.json").read_text(encoding="utf-8"))
            for test in suite:
                if test["id"] not in job["skip"] or test["do"] == "repeat":
                    self.run_test(job_id, test)
        self.emit(event="job_end", job_id=job_id)

    def run_test(self, job_id, test):
        action = test["do"]
        if action == "stall":
            time.sleep(FOREVER_SECONDS)
        self.emit(event="case_start", job_id=job_id, case_id=test["id"])
        if self.startup == "early-end":
            return
        ids = {"job_id": job_id, "case_id": test["id"], "duration_ns": 1000}
        if action in ("pass", "repeat"):
            self.emit(event="case_result", status="ok", **ids)
        elif action == "fail":
            self.emit(event="case_result", status="failed", message="assert 1 == 2", **ids)
        elif action == "raise":
            error = {"type": "KeyError", "message": "'x'", "trace": "tests/test_a.py:3 in test"}
            self.emit(event="case_result", status="error", error=error, **ids)
        elif action == "skip":
            self.emit(event="case_result", status="skipped", message="later", **ids)
        elif action == "environment":
            value = os.environ.get(test["variable"], "")
            self.emit(event="case_result", status="ok", stdout=value, **ids)
        elif action == "output":
            self.emit(event="case_result", status="ok", output=1, **ids)
        elif action == "hang":
            time.sleep(FOREVER_SECONDS)
        elif action == "sleep":
            time.sleep(test["seconds"])
            self.emit(event="case_result", status="ok", **ids)
        elif action == "crash":
            print("crashed", file=sys.stderr, flush=True)
            sys.exit(CRASH_EXIT_CODE)


if __name__ == "__main__":
    sys.exit(main())
