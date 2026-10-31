"""Probes and processes for the per-project lock
(docs/specs/installation-and-workspaces.md#project-folders).

The workers run in processes of their own, started with `spawn`, so they live in a module that a
new interpreter can import by name.
"""

import fcntl
import os
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from pathlib import Path

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, submit_project
from coding_study.domain.project_tests import LevelTests
from tests.fakes import make_environment
from tests.project_fakes import (
    PROJECT_SLUG,
    ScriptedProjectProcess,
    expected_answers,
    project_toolchains,
)

PROJECT_LOCK = f".cs/projects/{PROJECT_SLUG}.lock"


def lock_is_held(path: Path) -> bool:
    """Whether another descriptor, in this process or another, holds an exclusive lock on
    `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(descriptor)
    return False


class LockProbe:
    """A test generator that records, at each call, whether the project's lock was held."""

    def __init__(self, lock: Path) -> None:
        self._lock = lock
        self.held: list[bool] = []

    def generate(self, tests: LevelTests) -> str:
        self.held.append(lock_is_held(self._lock))
        return f"# level {tests.level}\n"


def passing_environment(root: Path) -> Environment:
    """The fixture project problem in the workspace `root`, every graded case answered right."""
    process = ScriptedProjectProcess()
    toolchains = project_toolchains(PythonTestGenerator())
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    process.answer = expected_answers(environment.problems.load(PROJECT_SLUG))
    return environment


def submit_at_once(root: Path, barrier: Barrier, opened: "Queue[int | None]") -> None:
    """Submits a passing solution once every worker is ready; puts the level it opened."""
    environment = passing_environment(root)
    barrier.wait()
    result = submit_project(environment, SubmitRequest(), [].append)
    opened.put(None if result.opened is None else result.opened.level)


def start_at_once(root: Path, barrier: Barrier, attempts: "Queue[int]") -> None:
    """Starts the problem once every worker is ready; puts the attempt it began or resumed."""
    environment = passing_environment(root)
    barrier.wait()
    attempts.put(start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt.id)
