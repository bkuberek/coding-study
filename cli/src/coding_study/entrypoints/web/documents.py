"""The documents of the API that no command prints (docs/specs/web-ui.md#endpoints)."""

from coding_study.application.attempt_files import AttemptTree, FileContent, ScopedFile
from coding_study.application.environment import Environment
from coding_study.application.problem_details import ProblemDetails
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import Language, ProblemKind, Track
from coding_study.entrypoints.commands._events import EVENTS_VERSION
from coding_study.entrypoints.web.markdown import render_markdown

API_VERSION = 1
"""Changes only when a response changes incompatibly (docs/specs/web-ui.md#api-conventions)."""
ITEM_KIND = "item"
"""The kind `cstudy list --kind` gives the non-autograded items."""


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


def _file_value(file: ScopedFile) -> dict[str, JsonValue]:
    return {
        "path": file.path,
        "origin": file.origin.value,
        "level": file.level,
        "state": file.state.value if file.state else None,
    }
