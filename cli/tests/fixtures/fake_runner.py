"""A scriptable stand-in for a language runner (docs/specs/runners.md), for SubprocessRunner tests.

Each case input holds one `step` that says what the "user code" does:

    {"do": "return", "value": V}   case_result ok with output V
    {"do": "raise", "message": M}  case_result error
    {"do": "invalid"}              case_result invalid_output
    {"do": "hang"}                 sleeps after case_start
    {"do": "stall"}                sleeps before case_start
    {"do": "crash", "exit_code": N} writes "crashed" to stderr and exits after case_start

A job whose target path ends in "missing.py" gets a load_error. `--startup` misbehaves before
any job runs: silent, exit-before-hello, bad-request, garbage, protocol-2, unknown-job, skip-cases.
"""

import argparse
import json
import sys
import time
from pathlib import Path

FOREVER_SECONDS = 3600


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
        if self.startup == "silent":
            time.sleep(FOREVER_SECONDS)
        if self.startup == "exit-before-hello":
            print("cannot start", file=sys.stderr)
            return 1
        protocol = 2 if self.startup == "protocol-2" else 1
        self.emit(event="hello", runner="fake", protocol=protocol, runtime="0.1")
        if self.startup == "bad-request":
            return 2
        if self.startup == "garbage":
            self.out.write("not json\n")
            self.out.flush()
            time.sleep(FOREVER_SECONDS)
        if self.startup == "unknown-job":
            self.emit(event="job_start", job_id="nope")
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        for job in request["jobs"]:
            self.run_job(job)
        self.emit(event="bye")
        return 0

    def run_job(self, job):
        job_id = job["job_id"]
        self.emit(event="job_start", job_id=job_id)
        if job["target"]["path"].endswith("missing.py"):
            error = {"type": "FileNotFoundError", "message": "missing.py"}
            self.emit(event="load_error", job_id=job_id, error=error)
        elif self.startup != "skip-cases":
            for case in job["cases"]:
                self.run_case(job_id, case["id"], case["input"]["step"])
        self.emit(event="job_end", job_id=job_id)

    def run_case(self, job_id, case_id, step):
        action = step["do"]
        if action == "stall":
            time.sleep(FOREVER_SECONDS)
        self.emit(event="case_start", job_id=job_id, case_id=case_id)
        ids = {"job_id": job_id, "case_id": case_id, "duration_ns": 1000, "stdout": ""}
        if action == "return":
            self.emit(event="case_result", status="ok", output=step["value"], **ids)
        elif action == "raise":
            error = {"type": "ValueError", "message": step["message"]}
            self.emit(event="case_result", status="error", error=error, **ids)
        elif action == "invalid":
            self.emit(event="case_result", status="invalid_output", reason="cyclic", **ids)
        elif action == "hang":
            time.sleep(FOREVER_SECONDS)
        elif action == "crash":
            print("crashed", file=sys.stderr, flush=True)
            sys.exit(step["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
