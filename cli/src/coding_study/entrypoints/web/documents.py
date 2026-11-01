"""The documents of the API that no command prints (docs/specs/web-ui.md#endpoints)."""

from coding_study.application.attempt_files import AttemptTree, FileContent, ScopedFile
from coding_study.application.complete_attempt import FinishedAttempt
from coding_study.application.environment import Environment
from coding_study.application.mock_interview import (
    CurrentMock,
    MockAttempt,
    MockProblem,
    MockSession,
)
from coding_study.application.problem_details import ProblemDetails
from coding_study.application.reveal_hint import HintsLocked, RevealedHint
from coding_study.domain.cases import JsonValue
from coding_study.domain.items import entry_kind
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta, Track
from coding_study.entrypoints.commands._events import EVENTS_VERSION
from coding_study.entrypoints.commands.list_problems import selected_jdk_value
from coding_study.entrypoints.commands.mock import nothing_message
from coding_study.entrypoints.commands.next_problem import pick_reason
from coding_study.entrypoints.web.markdown import render_markdown

API_VERSION = 1
"""Changes only when a response changes incompatibly (docs/specs/web-ui.md#api-conventions)."""
ITEM_KIND = "item"
"""The kind `cstudy list --kind` gives the non-autograded items."""
MOCK_LOCKS = ("hint", "solution", "mock")
"""What a running mock interview locks, as `cstudy hint`, `cstudy solution` and `cstudy mock`."""


def session_document(environment: Environment, port: int, version: str) -> dict[str, object]:
    """`GET /api/v1/session`: the server, its workspace, and the values the page's filters and
    forms offer."""
    return {
        "api": API_VERSION,
        "cstudy": version,
        "events_version": EVENTS_VERSION,
        "workspace": str(environment.root),
        "port": port,
        "default_lang": environment.config.default_lang.value,
        "languages": [language.value for language in Language],
        "tracks": [track.value for track in Track],
        "kinds": [*(kind.value for kind in ProblemKind), ITEM_KIND],
        "selected_jdk": selected_jdk_value(environment.jdk.selected()),
    }


def problem_document(entry: dict[str, JsonValue], details: ProblemDetails) -> dict[str, JsonValue]:
    """`GET /api/v1/problems/{slug}`: the problem's `cstudy list --json` entry, its `languages`
    the ones `cstudy start` accepts instead of the reference languages."""
    approaches: list[JsonValue] = [
        {"id": approach.id, "name": approach.name, "role": approach.role.value}
        for approach in details.approaches
    ]
    last_level = details.last_level
    return {
        **entry,
        "languages": [language.value for language in details.languages],
        "approaches": approaches,
        "broken": list(details.broken),
        "levels": None if last_level is None else {"last": last_level},
        "hints_total": details.hints_total,
        "bench": details.bench,
        "oracle": details.oracle,
    }


def markdown_document(markdown: str) -> dict[str, JsonValue]:
    """Markdown and the HTML the page shows of it."""
    return {"markdown": markdown, "html": render_markdown(markdown)}


def tree_document(tree: AttemptTree) -> dict[str, JsonValue]:
    """`GET /api/v1/attempts/{id}/files`: the attempt's root and its files in path order."""
    entries: list[JsonValue] = [
        {**_file_value(found.file), "size": found.size, "editable": found.editable}
        for found in tree.files
    ]
    return {"root": tree.root, "entries": entries}


def file_document(content: FileContent) -> dict[str, JsonValue]:
    """`GET /api/v1/attempts/{id}/files/{path}`."""
    value = _file_value(content.file)
    return {
        "path": value["path"],
        "text": content.text,
        "sha256": content.sha256,
        "origin": value["origin"],
        "level": value["level"],
        "state": value["state"],
        "editable": content.editable,
    }


def hint_document(revealed: RevealedHint | HintsLocked | None) -> dict[str, JsonValue]:
    """`POST /api/v1/attempts/{id}/hints`: the hint, the level a project's next hint opens
    with, or that every hint is revealed, as `cstudy hint` prints them."""
    if revealed is None:
        return {"exhausted": True}
    if isinstance(revealed, HintsLocked):
        return {"locked_until_level": revealed.level}
    text = markdown_document(revealed.text)
    return {"hint": {"number": revealed.number, "total": revealed.total, **text}}


def done_document(finished: FinishedAttempt) -> dict[str, JsonValue]:
    """`POST /api/v1/attempts/{id}/done`: the values of the two lines `cstudy done` prints."""
    attempt = finished.attempt
    assert attempt.ended_at is not None
    schedule = finished.schedule
    return {
        "slug": attempt.slug,
        "language": attempt.language.value if attempt.language else None,
        "status": attempt.status.value,
        "levels_finished": finished.project.finished if finished.project else None,
        "solve_s": int(attempt.solve_time(attempt.ended_at).total_seconds()),
        "rating": attempt.rating.value if attempt.rating else None,
        "grade": attempt.grade.name.lower() if attempt.grade is not None else None,
        "caps": [cap.value for cap in finished.caps],
        "hints_used": attempt.hints_used,
        "next_review": {
            "due_on": schedule.due_on.isoformat(),
            "in_days": (schedule.due_on - finished.today).days,
            "ease": schedule.state.ease,
        },
    }


def started_mock_document(session: MockSession) -> dict[str, JsonValue]:
    """`POST /api/v1/mock`: the problems `cstudy mock` started, each as its report lists it, or
    its message when nothing was in scope."""
    request = session.request
    ends_at = session.ends_at
    problems: list[JsonValue] = [_mock_problem_value(problem) for problem in session.problems]
    return {
        "minutes": request.minutes,
        "count": request.count,
        "language": session.language.value,
        "ends_at": ends_at.isoformat() if ends_at else None,
        "problems": problems,
        "message": None if problems else nothing_message(session),
    }


def running_mock_document(mock: CurrentMock | None) -> dict[str, JsonValue]:
    """`GET /api/v1/mock`: the mock whose timer runs, with the unfinished problems its lock
    names, in the order they started."""
    if mock is None:
        return {"running": False}
    attempts: list[JsonValue] = [_mock_attempt_value(started) for started in mock.attempts]
    return {
        "running": True,
        "ends_at": mock.ends_at.isoformat(),
        "remaining_s": int(mock.remaining.total_seconds()),
        "attempts": attempts,
        "locked": list(MOCK_LOCKS),
    }


def _mock_problem_value(problem: MockProblem) -> JsonValue:
    candidate = problem.pick.candidate
    return {
        "slug": candidate.slug,
        "title": problem.started.meta.title,
        "difficulty": candidate.difficulty.value,
        "group": candidate.group.name,
        "reason": pick_reason(problem.pick),
        "attempt_id": problem.started.attempt.id,
        "kind": _mock_kind(problem.started),
        "file": problem.user_file,
        "statement": problem.statement,
    }


def _mock_attempt_value(started: MockAttempt) -> JsonValue:
    attempt, meta = started.attempt, started.meta
    return {
        "attempt_id": attempt.id,
        "slug": attempt.slug,
        "title": meta.title,
        "difficulty": meta.difficulty.value,
        "kind": _mock_kind(started),
        "language": attempt.language.value if attempt.language else None,
    }


def _mock_kind(started: MockAttempt) -> str:
    """As `cstudy list --json` names it: `item` for an item."""
    meta = started.meta
    return entry_kind(meta.kind).value if isinstance(meta, ProblemMeta) else ITEM_KIND


def _file_value(file: ScopedFile) -> dict[str, JsonValue]:
    return {
        "path": file.path,
        "origin": file.origin.value,
        "level": file.level,
        "state": file.state.value if file.state else None,
    }
