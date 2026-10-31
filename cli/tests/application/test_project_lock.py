"""The per-project lock: `cstudy start` and the unlock of `cstudy submit` write a project's
generated files, its manifest and its levels one at a time
(docs/specs/installation-and-workspaces.md#project-folders)."""

import multiprocessing
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from coding_study.application.environment import Environment
from coding_study.application.project_manifest import ProjectManifests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, SubmitResult, submit_project
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.runs import CaseOutcome, RunCase, RunJob
from coding_study.domain.submissions import LevelUnlock
from tests.fakes import NOW, repository_root
from tests.helpers import PROJECT_PROBLEMS
from tests.project_fakes import (
    PROJECT_FOLDER,
    PROJECT_SLUG,
    ScriptedProjectProcess,
    project_toolchains,
)
from tests.project_locks import (
    PROJECT_LOCK,
    LockProbe,
    lock_is_held,
    passing_environment,
    start_at_once,
    submit_at_once,
)

EARLIER = NOW - timedelta(minutes=5)
WORKERS = 4
JOIN_SECONDS = 60.0


@pytest.fixture
def environment(tmp_path) -> Environment:
    return passing_environment(repository_root(tmp_path, PROJECT_PROBLEMS))


@pytest.fixture
def probe(environment) -> LockProbe:
    return LockProbe(environment.workspace.absolute(PROJECT_LOCK))


def probed(environment: Environment, probe: LockProbe) -> Environment:
    return replace(environment, toolchains=project_toolchains(probe))


def in_progress(environment: Environment) -> Attempt:
    found = environment.progress.active_attempt()
    assert found is not None
    return found


def submit(environment: Environment) -> SubmitResult:
    return submit_project(environment, SubmitRequest(), [].append)


def meanwhile(environment: Environment, change: Callable[[Attempt], Attempt]) -> None:
    """While the submission is graded, another command changes the attempt once."""
    process = cast(ScriptedProjectProcess, environment.runner_process)
    answer = process.answer
    changed: list[Attempt] = []

    def answer_after_the_change(job: RunJob, case: RunCase) -> CaseOutcome:
        if not changed:
            changed.append(change(in_progress(environment)))
            environment.progress.update_attempt(changed[0])
        return answer(job, case)

    process.answer = answer_after_the_change


def test_start_writes_level_1s_tests_under_the_projects_lock(environment, probe):
    start_attempt(probed(environment, probe), StartRequest(PROJECT_SLUG))
    assert probe.held == [True]


def test_a_resumed_start_writes_back_tests_under_the_projects_lock(environment, probe):
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    environment.workspace.absolute(f"{PROJECT_FOLDER}/tests/test_level_1.py").unlink()
    start_attempt(probed(environment, probe), StartRequest(PROJECT_SLUG))
    assert probe.held == [True]


def test_an_unlock_writes_the_opened_levels_tests_under_the_projects_lock(environment, probe):
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    submit(probed(environment, probe))
    assert probe.held == [True]


def test_grading_runs_without_the_projects_lock(environment):
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    held: list[bool] = []

    def note_the_lock(attempt: Attempt) -> Attempt:
        held.append(lock_is_held(environment.workspace.absolute(PROJECT_LOCK)))
        return attempt

    meanwhile(environment, note_the_lock)
    submit(environment)
    assert held == [False]


def test_a_submission_opens_nothing_once_another_opened_the_level(environment):
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    meanwhile(environment, lambda attempt: replace(attempt, level_unlocked=2))
    assert submit(environment).opened is None


def test_a_submission_opens_no_level_past_one_another_opened(environment):
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    meanwhile(environment, lambda attempt: replace(attempt, level_unlocked=2))
    submit(environment)
    assert in_progress(environment).level_unlocked == 2


def test_a_submission_opens_nothing_once_its_attempt_ended(environment):
    attempt_id = start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt.id
    meanwhile(environment, lambda attempt: replace(attempt, status=AttemptStatus.ABANDONED))
    submit(environment)
    assert environment.progress.level_unlocks(attempt_id) == (LevelUnlock(attempt_id, 1, NOW),)


def test_a_full_pass_keeps_the_first_pass_another_submission_recorded(environment):
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    attempt = in_progress(environment)
    environment.progress.update_attempt(replace(attempt, level_unlocked=2))
    meanwhile(environment, lambda attempt: replace(attempt, first_pass_at=EARLIER))
    assert submit(environment).attempt.first_pass_at == EARLIER


# real concurrency: processes of their own on one workspace


def race(root: Path, worker: Callable[..., None]) -> list[object]:
    """Runs `worker` in WORKERS processes that pass a barrier together; returns what each put."""
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(WORKERS)
    results = context.Queue()
    processes = [
        context.Process(target=worker, args=(root, barrier, results)) for _ in range(WORKERS)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(JOIN_SECONDS)
    assert [process.exitcode for process in processes] == [0] * WORKERS
    return [results.get(timeout=JOIN_SECONDS) for _ in processes]


@pytest.fixture(scope="module")
def raced_submissions(tmp_path_factory) -> tuple[Environment, list[object]]:
    root = repository_root(tmp_path_factory.mktemp("submissions"), PROJECT_PROBLEMS)
    environment = passing_environment(root)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment, race(root, submit_at_once)


@pytest.mark.slow
def test_concurrent_passing_submissions_open_the_next_level_once(raced_submissions):
    _, opened = raced_submissions
    assert sorted(opened, key=str) == [2] + [None] * (WORKERS - 1)


@pytest.mark.slow
def test_concurrent_passing_submissions_record_one_unlock_per_level(raced_submissions):
    environment, _ = raced_submissions
    attempt = in_progress(environment)
    assert [unlock.level for unlock in environment.progress.level_unlocks(attempt.id)] == [1, 2]


@pytest.mark.slow
def test_concurrent_passing_submissions_leave_level_2_open(raced_submissions):
    environment, _ = raced_submissions
    assert in_progress(environment).level_unlocked == 2


@pytest.mark.slow
def test_concurrent_passing_submissions_leave_a_readable_manifest(raced_submissions):
    environment, _ = raced_submissions
    manifest = ProjectManifests(environment.workspace).load(PROJECT_SLUG)
    assert manifest is not None
    assert manifest.file("tests/test_level_2.py") is not None


@pytest.fixture(scope="module")
def raced_starts(tmp_path_factory) -> tuple[Environment, list[object]]:
    """The progress database exists first: the race is over the project, not over migrating a
    new database."""
    root = repository_root(tmp_path_factory.mktemp("starts"), PROJECT_PROBLEMS)
    environment = passing_environment(root)
    environment.progress.active_attempt()
    return environment, race(root, start_at_once)


@pytest.mark.slow
def test_concurrent_starts_begin_one_attempt(raced_starts):
    _, attempts = raced_starts
    assert len(set(attempts)) == 1


@pytest.mark.slow
def test_concurrent_starts_leave_one_attempt_in_progress(raced_starts):
    environment, _ = raced_starts
    rows = environment.progress.snapshot().tables["attempts"]
    assert [row["status"] for row in rows] == [AttemptStatus.IN_PROGRESS]
