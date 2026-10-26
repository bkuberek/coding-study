"""A small but real runner for Python files (docs/specs/runners.md), for end-to-end CLI tests.

It speaks the protocol for function and class kinds with plain JSON values (no node types):
loads the target file, calls the function or replays the operations, captures standard output,
and reports `ok`, `error` (with `op_index` and `partial_output` for class kinds),
`invalid_output` for values JSON cannot encode, or `load_error`.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    request = json.loads(Path(arguments.request).read_text(encoding="utf-8"))
    with Path(arguments.out).open("w", encoding="utf-8") as out:
        events = Events(out)
        events.emit(event="hello", runner="mini-python", protocol=1, runtime=sys.version.split()[0])
        for job in request["jobs"]:
            run_job(events, job)
        events.emit(event="bye")
    return 0


class Events:
    def __init__(self, out):
        self.out = out

    def emit(self, **event):
        self.out.write(json.dumps(event) + "\n")
        self.out.flush()


def run_job(events, job):
    job_id = job["job_id"]
    events.emit(event="job_start", job_id=job_id)
    try:
        target = load_target(job)
    except Exception as error:
        events.emit(event="load_error", job_id=job_id, error=describe(error))
    else:
        for case in job["cases"]:
            events.emit(event="case_start", job_id=job_id, case_id=case["id"])
            result = run_case(job, target, case)
            events.emit(event="case_result", job_id=job_id, case_id=case["id"], **result)
    events.emit(event="job_end", job_id=job_id)


def load_target(job):
    path = Path(job["target"]["path"])
    spec = importlib.util.spec_from_file_location(f"target_{abs(hash(path))}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = job["names"]
    symbol = names["function"] if job["kind"] == "function" else names["class"]
    if not hasattr(module, symbol):
        raise AttributeError(f"{path.name} defines no {symbol}")
    return getattr(module, symbol)


def run_case(job, target, case):
    stdout = io.StringIO()
    outputs = []
    started = time.perf_counter_ns()
    try:
        with contextlib.redirect_stdout(stdout):
            if job["kind"] == "function":
                params = job["signature"]["function"]["params"]
                output = target(*(case["input"][param["name"]] for param in params))
            else:
                output = replay(job, target, case, outputs)
    except Exception as error:
        result = {"status": "error", "error": describe(error)}
        if job["kind"] != "function":
            result.update(op_index=len(outputs), partial_output=outputs)
        return finish(result, started, stdout)
    try:
        json.dumps(output, allow_nan=False)
    except (TypeError, ValueError) as error:
        return finish({"status": "invalid_output", "reason": str(error)}, started, stdout)
    return finish({"status": "ok", "output": output}, started, stdout)


def replay(job, target, case, outputs):
    methods = job["names"]["methods"]
    instance = target(*case["args"][0])
    outputs.append(None)
    for name, args in zip(case["ops"][1:], case["args"][1:], strict=True):
        outputs.append(getattr(instance, methods[name])(*args))
    return list(outputs)


def finish(result, started, stdout):
    return {**result, "duration_ns": time.perf_counter_ns() - started, "stdout": stdout.getvalue()}


def describe(error):
    return {"type": type(error).__name__, "message": str(error)}


if __name__ == "__main__":
    sys.exit(main())
