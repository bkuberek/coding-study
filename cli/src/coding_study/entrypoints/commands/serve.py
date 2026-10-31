"""`cstudy serve` (docs/specs/cli.md#cstudy-serve): the local web UI, on 127.0.0.1 only.

The web stack is imported inside the command, so no other command loads Starlette or uvicorn
(NFR-2, docs/architecture.md#web-adapter).
"""

import html
import os
import webbrowser
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.locations import WORKSPACE_VARIABLE
from coding_study.adapters.preferences_fs import SERVE_DIRECTORY, FsPreferencesStore
from coding_study.adapters.serve_install import InstalledWebUi
from coding_study.adapters.workspace_marker import tool_version
from coding_study.application.environment import Environment
from coding_study.application.ports import WebUiInstall
from coding_study.entrypoints.shared import (
    ExitCode,
    GlobalOptions,
    add_command,
    command_environ,
    console,
    print_error,
)

NAME = "serve"
MAX_PORT = 65535
LABEL_WIDTH = 11
TERMINATED_EXIT_CODE = 143
"""128 + SIGTERM, as a shell reports a process that SIGTERM ended."""
REINSTALL = "reinstall cstudy"
OWNER_ONLY = 0o600


class WebUiNotInstalledError(Exception):
    """The web server libraries or the page's assets are missing (exit code 4)."""


class ServerStoppedError(Exception):
    """The server stopped without a signal, as when it fails to start (exit code 70)."""


def register(app: typer.Typer) -> None:
    add_command(app, serve, NAME)


def serve(
    context: typer.Context,
    port: Annotated[
        int,
        typer.Option("--port", min=0, max=MAX_PORT, metavar="N", help="Default: a free port (0)."),
    ] = 0,
    open_browser: Annotated[
        bool, typer.Option("--open", help="Open the page in the default browser.")
    ] = False,
) -> None:
    """Serve the local web UI on 127.0.0.1."""
    environ = command_environ(context)
    home = Path.home()
    root = load_environment(Path.cwd(), environ, home).root
    from coding_study.entrypoints.web import STATIC_DIRECTORY

    _require_installed(InstalledWebUi(STATIC_DIRECTORY))
    from coding_study.entrypoints.web import server
    from coding_study.entrypoints.web.app import create_app
    from coding_study.entrypoints.web.children import ChildCommand
    from coding_study.entrypoints.web.context import ServerSettings
    from coding_study.entrypoints.web.runs import Children
    from coding_study.entrypoints.web.security import SessionSecrets, login_url

    try:
        listener = server.bind_loopback(port)
    except server.PortInUseError as error:
        _environment_error(error)
    with listener, server.stop_signals():
        secrets = SessionSecrets.generate()
        settings = ServerSettings(
            port=listener.getsockname()[1],
            version=tool_version(),
            secrets=secrets,
            static_directory=STATIC_DIRECTORY,
            load_environment=_workspace_environment(root, environ, home),
            preferences=FsPreferencesStore(root),
            child=ChildCommand(content=context.ensure_object(GlobalOptions).content),
        )
        output = console(context)
        output.print(Text(f"cstudy serve {settings.version} · workspace {_shown(root, home)}"))
        url = login_url(settings.port, secrets.token)
        output.print(_line("open", url))
        redirect = _open_in_browser(root, settings.port, url) if open_browser else None
        children = Children(report=lambda label, text: output.print(_line(label, text)))
        try:
            server.serve_forever(create_app(settings, children), listener, children.stop)
        except KeyboardInterrupt:
            _stop(output, "Ctrl-C", ExitCode.INTERRUPTED)
        except server.Terminated:
            _stop(output, "SIGTERM", TERMINATED_EXIT_CODE)
        finally:
            if redirect is not None:
                redirect.unlink(missing_ok=True)
    print_error(ServerStoppedError("the web server stopped without being asked to"))
    raise typer.Exit(ExitCode.INTERNAL_ERROR)


def _require_installed(web: WebUiInstall) -> None:
    libraries = web.server_libraries()
    if libraries.problem is not None:
        _environment_error(
            WebUiNotInstalledError(
                f"the web server libraries are missing: {libraries.problem}; fix: {REINSTALL}"
            )
        )
    assets = web.assets()
    if assets.problem is not None:
        _environment_error(
            WebUiNotInstalledError(
                f"the page's assets do not match their manifest: {assets.problem}; fix: {REINSTALL}"
            )
        )


def _environment_error(error: Exception) -> NoReturn:
    print_error(error)
    raise typer.Exit(ExitCode.ENVIRONMENT_ERROR)


def _workspace_environment(
    root: Path, environ: Mapping[str, str], home: Path
) -> Callable[[], Environment]:
    """A fresh Environment of the server's workspace for each use case call, with the workspace
    pinned, since a relative CSTUDY_WORKSPACE would resolve against another directory."""
    pinned = {**environ, WORKSPACE_VARIABLE: str(root)}
    return lambda: load_environment(root, pinned, home)


def _shown(path: Path, home: Path) -> str:
    """`~/cstudy-workspace` for a path under the home directory."""
    if not path.is_relative_to(home):
        return str(path)
    return str(Path("~") / path.relative_to(home))


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line


def _open_in_browser(root: Path, port: int, url: str) -> Path:
    """Writes `.cs/serve/<port>.html`, readable by its owner only, which redirects to `url`, and
    opens it, so the token never appears in the arguments of the process that opens the
    browser. Returns the file, which the server removes when it stops."""
    path = root / SERVE_DIRECTORY / f"{port}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
    with os.fdopen(os.open(path, flags, OWNER_ONLY), "w", encoding="utf-8") as redirect:
        os.fchmod(redirect.fileno(), OWNER_ONLY)
        redirect.write(_redirect_page(url))
    webbrowser.open(path.as_uri())
    return path


def _redirect_page(url: str) -> str:
    target = html.escape(url)
    return (
        "<!doctype html>\n"
        '<meta charset="utf-8">\n'
        f'<meta http-equiv="refresh" content="0; url={target}">\n'
        "<title>cstudy</title>\n"
        f'<a href="{target}">Open cstudy</a>\n'
    )


def _stop(output: Console, how: str, exit_code: int) -> NoReturn:
    output.print(_line("stop", how))
    raise typer.Exit(exit_code) from None
