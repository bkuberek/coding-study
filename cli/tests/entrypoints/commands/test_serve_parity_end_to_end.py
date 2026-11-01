"""The practice commands an attempt goes through, from the page, for every kind in every language
(docs/specs/web-ui.md#command-parity): through a real `cstudy serve`, the page's API starts one
problem of each kind in each of the six languages, runs its tests as the page does, in a child
`cstudy test --events`, and finishes the attempt with Done.

Each problem is a quick one of its kind in that language, played from its starting code: the
stub, or a debugging problem's planted bug, fails its cases, so Done gives up, unless a run
passed. The workspace shares the session's practice workspace's toolchains, and the runs go one
at a time, as the JVM languages share one Gradle build."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.scripted_runs import Frame
from tests.serve_page import Page, opened_page
from tests.serve_process import running_server
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

LANGUAGES = ("python", "typescript", "java", "kotlin", "go", "rust")
DEBUGGING_FUNCTIONS = ("python", "typescript", "java", "kotlin")
PROBLEMS: dict[str, dict[str, str]] = {
    "function": dict.fromkeys(LANGUAGES, "two-sum"),
    "design": dict.fromkeys(LANGUAGES, "min-stack"),
    "progressive": dict.fromkeys(LANGUAGES, "transactional-kv-store"),
    "concurrent": dict.fromkeys(LANGUAGES, "bounded-blocking-queue"),
    "debugging": {
        **dict.fromkeys(DEBUGGING_FUNCTIONS, "debug-binary-search-bounds"),
        "go": "debug-shadowed-variable",
        "rust": "debug-unsigned-underflow",
    },
    "project": {language: f"bank-project-{language}" for language in LANGUAGES},
}
"""One problem per kind and language; a debugging problem is a function or design problem of the
`debugging` track."""
DEBUGGING = "debugging"
VERDICTS = ("passed", "failed")
RESULT_EVENTS = ("case_result", "test_result")


@dataclass(frozen=True)
class Row:
    kind: str
    language: str

    @property
    def slug(self) -> str:
        return PROBLEMS[self.kind][self.language]

    def __str__(self) -> str:
        return f"{self.kind}-{self.language}"


ROWS = [Row(kind, language) for kind in PROBLEMS for language in LANGUAGES]


@dataclass
class Walk:
    """What the page heard on one row's way from start to done."""

    started: int = 0
    attempt: dict[str, Any] = field(default_factory=dict[str, Any])
    frames: list[Frame] = field(default_factory=list[Frame])
    finished: int = 0
    done: dict[str, Any] = field(default_factory=dict[str, Any])

    @property
    def run_end(self) -> dict[str, Any]:
        return next((frame.data for frame in self.frames if frame.event == "run_end"), {})


@pytest.fixture(scope="module")
def walks(
    practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[dict[Row, Walk]]:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("parity") / "workspace")
    with running_server(root) as server:
        page = opened_page(server)
        yield {row: _walk(page, row) for row in ROWS}
        page.client.close()


def _walk(page: Page, row: Row) -> Walk:
    """Start, test and done from the page; a step the page could not take leaves the rest."""
    walk = Walk()
    started = page.start_attempt(row.slug, row.language)
    walk.started, walk.attempt = started.status_code, started.json()
    if walk.started != 201:
        return walk
    walk.frames = page.played(page.started(row.slug))
    passed = walk.run_end.get("outcome") == "passed" and row.kind != "project"
    finished = page.finish(row.slug, {"rating": "ok"} if passed else {"gave_up": True})
    walk.finished, walk.done = finished.status_code, finished.json()
    return walk


def kind_of(document: dict[str, Any]) -> str:
    """The matrix's kind of an attempt or a run: `debugging` for the track, else the kind."""
    return DEBUGGING if document.get("track") == DEBUGGING else document.get("kind", "")


@pytest.mark.parametrize("row", ROWS, ids=str)
def test_start_from_the_page_opens_an_attempt_of_the_kind(walks, row):
    walk = walks[row]
    assert (walk.started, kind_of(walk.attempt), walk.attempt.get("language")) == (
        201,
        row.kind,
        row.language,
    )


@pytest.mark.parametrize("row", ROWS, ids=str)
def test_a_run_from_the_page_starts_on_the_attempt(walks, row):
    run_start = walks[row].frames[0].data
    assert (run_start["attempt_id"], kind_of(run_start)) == (
        walks[row].attempt["attempt_id"],
        row.kind,
    )


@pytest.mark.parametrize("row", ROWS, ids=str)
def test_a_run_from_the_page_reaches_a_verdict(walks, row):
    assert walks[row].run_end.get("outcome") in VERDICTS


@pytest.mark.parametrize("row", ROWS, ids=str)
def test_a_run_from_the_page_streams_its_results(walks, row):
    assert any(frame.event in RESULT_EVENTS for frame in walks[row].frames)


@pytest.mark.parametrize("row", ROWS, ids=str)
def test_a_run_from_the_page_closes_with_the_exit_code_of_its_run_end(walks, row):
    closed = walks[row].frames[-1]
    assert (closed.event, closed.data["exit_code"]) == ("closed", walks[row].run_end["exit_code"])


@pytest.mark.parametrize("row", ROWS, ids=str)
def test_done_from_the_page_finishes_the_attempt(walks, row):
    walk = walks[row]
    assert (walk.finished, walk.done.get("slug"), walk.done.get("language")) == (
        200,
        row.slug,
        row.language,
    )
