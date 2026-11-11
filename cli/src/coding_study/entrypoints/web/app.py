"""The app factory: routes, error handlers and the security layer around them
(docs/specs/web-ui.md#server)."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from starlette.applications import Starlette
from starlette.types import ASGIApp

from coding_study.application.attempt_changes import WorkspaceSnapshot, workspace_snapshot
from coding_study.entrypoints.web.api_about import about_routes
from coding_study.entrypoints.web.api_attempts import attempt_routes
from coding_study.entrypoints.web.api_browsing import browsing_routes
from coding_study.entrypoints.web.api_code_intelligence import (
    code_intelligence_routes,
    warm_up,
)
from coding_study.entrypoints.web.api_config import config_routes
from coding_study.entrypoints.web.api_dev import dev_routes
from coding_study.entrypoints.web.api_events import event_routes
from coding_study.entrypoints.web.api_files import file_routes
from coding_study.entrypoints.web.api_health import health_routes
from coding_study.entrypoints.web.api_mock import mock_routes
from coding_study.entrypoints.web.api_past_files import past_file_routes
from coding_study.entrypoints.web.api_practice import practice_routes
from coding_study.entrypoints.web.api_progress import progress_routes
from coding_study.entrypoints.web.api_reset import reset_routes
from coding_study.entrypoints.web.api_runs import run_routes
from coding_study.entrypoints.web.api_session import session_routes
from coding_study.entrypoints.web.api_sets import set_routes
from coding_study.entrypoints.web.api_solutions import solution_routes
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from coding_study.entrypoints.web.context import ServerSettings, ServerState
from coding_study.entrypoints.web.errors import exception_handlers
from coding_study.entrypoints.web.notifications import (
    ChildNotices,
    Notifications,
    WorkspaceWatch,
)
from coding_study.entrypoints.web.page import front_end_routes
from coding_study.entrypoints.web.runs import Children
from coding_study.entrypoints.web.security import SecurityMiddleware


def create_app(
    settings: ServerSettings,
    children: Children | None = None,
    notifications: Notifications | None = None,
    sessions: LanguageSessions | None = None,
) -> ASGIApp:
    """`children` holds the runs and jobs, `notifications` the tabs' notification streams and
    `sessions` the code-intelligence sessions; stopping the children, which the server does first
    as it shuts down, ends those streams."""
    routes = [
        *front_end_routes(settings.static_directory, settings.secrets.csrf),
        *session_routes(),
        *about_routes(),
        *config_routes(),
        *browsing_routes(),
        *set_routes(),
        *attempt_routes(),
        *file_routes(),
        *past_file_routes(),
        *practice_routes(),
        *solution_routes(),
        *mock_routes(),
        *run_routes(),
        *dev_routes(),
        *health_routes(),
        *code_intelligence_routes(),
        *progress_routes(),
        *reset_routes(),
        *event_routes(),
    ]
    state = ServerState(
        settings,
        children=children or Children(),
        notifications=notifications or Notifications(),
        sessions=sessions or LanguageSessions(),
    )
    state.children.listen(ChildNotices(state.notifications))
    state.sessions.watch(state.notifications)
    app = Starlette(
        routes=routes, exception_handlers=exception_handlers(), lifespan=_serving(state)
    )
    app.state.server = state
    return SecurityMiddleware(app, settings.port, settings.secrets)


def _serving(state: ServerState) -> Callable[[Starlette], AbstractAsyncContextManager[None]]:
    """Watches the workspace while the server runs, and starts the default language's server
    ahead of time when the settings say so; then stops the runs and jobs, which ends the
    notification streams, the code-intelligence sessions, and the watch."""

    async def snapshot(previous: WorkspaceSnapshot | None) -> WorkspaceSnapshot:
        load_environment = state.settings.load_environment
        return await state.worker.run(lambda: workspace_snapshot(load_environment(), previous))

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncGenerator[None]:
        watch = WorkspaceWatch(state.notifications, state.settings.watcher, snapshot)
        watching = asyncio.create_task(watch.run())
        warming = asyncio.create_task(warm_up(state)) if state.settings.warm_up else None
        yield
        if warming is not None:
            warming.cancel()
            await asyncio.gather(warming, return_exceptions=True)
        await state.children.stop()
        await state.sessions.stop()
        state.notifications.stop()
        await watching

    return lifespan
