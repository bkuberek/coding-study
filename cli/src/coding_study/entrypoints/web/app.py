"""The app factory: routes, error handlers and the security layer around them
(docs/specs/web-ui.md#server)."""

from starlette.applications import Starlette
from starlette.types import ASGIApp

from coding_study.entrypoints.web.api_attempts import attempt_routes
from coding_study.entrypoints.web.api_browsing import browsing_routes
from coding_study.entrypoints.web.api_files import file_routes
from coding_study.entrypoints.web.api_health import health_routes
from coding_study.entrypoints.web.api_practice import practice_routes
from coding_study.entrypoints.web.api_progress import progress_routes
from coding_study.entrypoints.web.api_session import session_routes
from coding_study.entrypoints.web.context import ServerSettings, ServerState
from coding_study.entrypoints.web.errors import exception_handlers
from coding_study.entrypoints.web.page import front_end_routes
from coding_study.entrypoints.web.security import SecurityMiddleware


def create_app(settings: ServerSettings) -> ASGIApp:
    routes = [
        *front_end_routes(settings.static_directory, settings.secrets.csrf),
        *session_routes(),
        *browsing_routes(),
        *attempt_routes(),
        *file_routes(),
        *practice_routes(),
        *health_routes(),
        *progress_routes(),
    ]
    app = Starlette(routes=routes, exception_handlers=exception_handlers())
    app.state.server = ServerState(settings)
    return SecurityMiddleware(app, settings.port, settings.secrets)
