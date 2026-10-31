"""Runs `cs_runner` as `cstudy` launches a project job (docs/specs/runners.md#launch).

A project job imports the project's modules into the runner process, so each run is a process of
its own: `python -P -m cs_runner` with the project root as the working directory.
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from tests.runner_harness import COUNTER_SIGNATURE, Event, RunnerRun, request_of

RUNNER_TIMEOUT_SECONDS = 60
CONFORMANCE = Path(__file__).resolve().parents[2] / "conformance"


def write_project(root: Path, files: dict[str, str]) -> Path:
    """`files` by path relative to `root`; returns `root`."""
    for relative, source in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source), encoding="utf-8")
    return root


def conformance_project(fixture: str, approach: str, root: Path) -> Path:
    """The fixture's `starter/`, then its `solutions/<approach>/` overlay, copied into `root`."""
    directory = next(CONFORMANCE.glob(f"*-{fixture}"))
    shutil.copytree(directory / "starter", root)
    shutil.copytree(directory / "solutions" / approach, root, dirs_exist_ok=True)
    return root


def conformance_cases(fixture: str) -> list[Event]:
    directory = next(CONFORMANCE.glob(f"*-{fixture}"))
    document = json.loads((directory / "tests.json").read_text(encoding="utf-8"))
    return [{key: case[key] for key in ("id", "ops", "args")} for case in document["cases"]]


def project_job(
    root: Path, module: str, cases: list[Event], signature: Event = COUNTER_SIGNATURE
) -> Event:
    declared = signature["class"]
    methods = {method["name"]: method["name"] for method in declared["methods"]}
    return {
        "job_id": "project",
        "kind": "project",
        "target": {"project": str(root), "module": module},
        "names": {"class": declared["name"], "methods": methods},
        "signature": signature,
        "cases": cases,
    }


def suite_job(root: Path, **fields: Any) -> Event:
    job: Event = {
        "job_id": "project/suite",
        "kind": "suite",
        "framework": "pytest",
        "root": str(root),
        "exclude": [],
        "select": [],
        "skip": [],
    }
    return job | fields


def run_project(root: Path, *jobs: Event) -> RunnerRun:
    """The runner in `root`, with the bytecode cache outside it, as `cstudy` starts it."""
    run_directory = root.parent / "run"
    run_directory.mkdir(exist_ok=True)
    request = run_directory / "request.json"
    events = run_directory / "events.jsonl"
    request.write_text(json.dumps(request_of(*jobs)), encoding="utf-8")
    environment = os.environ | {
        "UV_NO_SYNC": "1",
        "PYTHONPYCACHEPREFIX": str(root.parent / "pycache"),
    }
    process = subprocess.run(
        [sys.executable, "-P", "-m", "cs_runner", "--request", str(request), "--out", str(events)],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=RUNNER_TIMEOUT_SECONDS,
        check=False,
    )
    lines = events.read_text(encoding="utf-8").splitlines()
    return RunnerRun(process.returncode, [json.loads(line) for line in lines])
