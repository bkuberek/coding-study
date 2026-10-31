"""A scriptable stand-in for a language runner (docs/specs/runners.md), for SubprocessRunner tests.

Each case input holds one `step` that says what the "user code" does:

    {"do": "return", "value": V}   case_result ok with output V
    {"do": "pass"}                 case_result ok without an output, as only a suite's test has
    {"do": "raise", "message": M}  case_result error
    {"do": "invalid"}              case_result invalid_output
    {"do": "hang"}                 sleeps after case_start
    {"do": "stall"}                sleeps before case_start
    {"do": "crash", "exit_code": N} writes "crashed" to stderr and exits after case_start
    {"do": "sleep", "seconds": S}  sleeps S seconds after case_start, then case_result ok with 0
    {"do": "stall", "seconds": S}  sleeps S seconds before case_start, then returns 0

A job whose target path ends in "missing.py" gets a load_error. `--startup` misbehaves before
any job runs: silent, exit-before-hello, bad-request, garbage, protocol-2, unknown-job, skip-cases.

Debug agents are imitated by four more startups, each logging one line to `--launch-log` and
talking about `--ready-line` and `--refused-line` (on `--ready-stream`):

    debug-wait    prints the ready line (or, given `--ready-file`, writes a port to that file,
                  which must be empty), then waits for the `--release` file to exist
    debug-detach  does what debug-wait does, then starts a process that sleeps, writes its pid
                  to `--leftover-pid` and exits 0, as `debugserver` does when lldb detaches. Like
                  the runner `debugserver` starts, that process leads a session and process group
                  of its own, and runs `--leftover-binary` (default: this interpreter)
    debug-refuse  prints the refused line to stderr and exits 2 until the `--release` file exists
    debug-exit    prints "address already in use" to stderr and exits 1
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

FOREVER_SECONDS = 3600
RELEASE_PATIENCE_SECONDS = 10
RELEASE_POLL_SECONDS = 0.01


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--startup", default="normal")
    parser.add_argument("--ready-line", default="agent listening")
    parser.add_argument("--ready-stream", default="stdout")
    parser.add_argument("--refused-line", default="connect refused")
    parser.add_argument("--release", default="")
    parser.add_argument("--launch-log", default="")
    parser.add_argument("--ready-file", default="")
    parser.add_argument("--leftover-pid", default="")
    parser.add_argument("--leftover-binary", default=sys.executable)
    arguments = parser.parse_args()
    with Path(arguments.out).open("w", encoding="utf-8") as out:
        return Runner(out, arguments).run(arguments.request)


class Runner:
    def __init__(self, out, arguments):
        self.out = out
        self.startup = arguments.startup
        self.arguments = arguments

    def debug_startup(self):
        """Returns an exit code when the imitated agent ends the process, else None."""
        arguments = self.arguments
        if arguments.launch_log:
            with Path(arguments.launch_log).open("a", encoding="utf-8") as log:
                log.write("launched\n")
        release = Path(arguments.release)
        if self.startup == "debug-exit":
            print("address already in use", file=sys.stderr, flush=True)
            return 1
        if self.startup == "debug-refuse" and not release.exists():
            print(arguments.refused_line, file=sys.stderr, flush=True)
            return 2
        if self.startup in ("debug-wait", "debug-detach"):
            if not self.say_ready():
                return 1
            deadline = time.monotonic() + RELEASE_PATIENCE_SECONDS
            while not release.exists():
                if time.monotonic() > deadline:
                    print("never released", file=sys.stderr, flush=True)
                    return 1
                time.sleep(RELEASE_POLL_SECONDS)
        if self.startup == "debug-detach":
            leftover = subprocess.Popen(
                [arguments.leftover_binary, "-c", f"import time; time.sleep({FOREVER_SECONDS})"],
                start_new_session=True,
            )
            Path(arguments.leftover_pid).write_text(str(leftover.pid), encoding="utf-8")
            return 0
        return None

    def say_ready(self):
        """False when the ready file is missing or still holds what an earlier launch wrote:
        `debugserver` writes to an existing file only."""
        arguments = self.arguments
        if arguments.ready_file:
            ready_file = Path(arguments.ready_file)
            if not ready_file.is_file() or ready_file.read_bytes():
                print("missing or stale ready file", file=sys.stderr, flush=True)
                return False
            ready_file.write_bytes(b"12345\0")
            return True
        stream = sys.stderr if arguments.ready_stream == "stderr" else sys.stdout
        print(arguments.ready_line, file=stream, flush=True)
        return True

    def emit(self, **event):
        self.out.write(json.dumps(event) + "\n")
        self.out.flush()

    def run(self, request_path):
        if self.startup.startswith("debug-"):
            exit_code = self.debug_startup()
            if exit_code is not None:
                return exit_code
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
            time.sleep(step.get("seconds", FOREVER_SECONDS))
            if "seconds" in step:
                action, step = "return", {"value": 0}
        self.emit(event="case_start", job_id=job_id, case_id=case_id)
        ids = {"job_id": job_id, "case_id": case_id, "duration_ns": 1000, "stdout": ""}
        if action == "return":
            self.emit(event="case_result", status="ok", output=step["value"], **ids)
        elif action == "pass":
            self.emit(event="case_result", status="ok", **ids)
        elif action == "raise":
            error = {"type": "ValueError", "message": step["message"]}
            self.emit(event="case_result", status="error", error=error, **ids)
        elif action == "invalid":
            self.emit(event="case_result", status="invalid_output", reason="cyclic", **ids)
        elif action == "hang":
            time.sleep(FOREVER_SECONDS)
        elif action == "sleep":
            time.sleep(step["seconds"])
            self.emit(event="case_result", status="ok", output=0, **ids)
        elif action == "crash":
            print("crashed", file=sys.stderr, flush=True)
            sys.exit(step["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
