"""The documents of the API that no command prints (docs/specs/web-ui.md#endpoints)."""

from coding_study.application.environment import Environment
from coding_study.domain.problem import Language, ProblemKind, Track
from coding_study.entrypoints.commands._events import EVENTS_VERSION

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
